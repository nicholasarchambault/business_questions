#!/usr/bin/env python
# coding: utf-8

# # Answering Business Questions Using SQL
# by Nicholas Archambault
# 
# This project will answer questions about the Chinook database, a collection of eleven tables of information on a fictional, digital iTunes-like music store. The data includes information on employees, customers, purchases and product information.

# ## Exploring the Data

# In[1]:


get_ipython().run_cell_magic('capture', '', '%load_ext sql\n%sql sqlite:///chinook.db')


# In[2]:


get_ipython().run_cell_magic('sql', '', 'SELECT\n    name,\n    type\nFROM sqlite_master\nWHERE type IN ("table","view");')


# ## Selecting Albums to Purchase
# 
# The fictional scenario at hand is as follows: the Chinook record store has just signed a deal with a new record label, and we are tasked with selecting the first three albums that will be added to the store, from a list of four. All four albums are by artists that don't have any tracks in the store right now -- we know the artist names and the genre of music they produce. The four genres from which to choose are Hip Hop, Punk, Pop, and Blues. 
# 
# The goal of this section is to identify which of these genres sell best in the United States, then make a recommendation for which three albums should be purchased of the four options.
# 
# Our query yields the number of tracks sold in the United States by genre, in terms of both absolute numbers and percentages of total tracks sold.

# In[3]:


get_ipython().run_cell_magic('sql', '', '\nWITH usa_tracks AS\n   (\n    SELECT il.* FROM invoice_line il\n    INNER JOIN invoice i on il.invoice_id = i.invoice_id\n    INNER JOIN customer c on i.customer_id = c.customer_id\n    WHERE c.country = "USA"\n   )\n\nSELECT\n      g.name genre,\n      COUNT(ut.invoice_line_id) tracks_sold,\n      ROUND(\n          CAST(COUNT(ut.invoice_line_id) AS FLOAT) / (\n            SELECT COUNT(*) FROM usa_tracks), \n          4) percentage_sold\nFROM  usa_tracks ut\nINNER JOIN track t on t.track_id = ut.track_id\nINNER JOIN genre g on g.genre_id = t.genre_id\nGROUP BY 1\nORDER BY 2 DESC\nLIMIT 10;')


# Based on this preliminary analysis, we should purchase the Punk, Blues, and Pop albums. We should keep in mind, though, that theses three genres make up just 17% of total tracks sold. A more promising category might be Rock, which accounts for 53% of total sales.

# ## Analyzing Employee Performance
# 
# Each customer for the Chinook store gets assigned to a sales support agent within the company when they first make a purchase. We can analyze the purchases of customers belonging to each employee to see if any sales support agent is performing either better or worse than the others.
# 
# It might prove useful to consider whether any extra columns from the employee table explain any variance that is seen, or whether the variance might instead be indicative of employee performance.

# In[4]:


get_ipython().run_cell_magic('sql', '', '\nWITH emp AS\n    (\n     SELECT\n         i.customer_id,\n         c.support_rep_id,\n         SUM(i.total) total\n     FROM invoice i\n     INNER JOIN customer c ON i.customer_id = c.customer_id\n     GROUP BY 1\n    )\n\nSELECT\n    (e.first_name || " " || e.last_name) employee,\n    e.hire_date,\n    ROUND(SUM(emp.total),2) total_sales\nFROM emp\nINNER JOIN employee e ON e.employee_id = emp.support_rep_id\nGROUP BY 1;')


# Analysis shows that there is a ~20% difference in sales performance between Jane and Steve. This difference, however, corresponds to the difference between their hiring dates, suggesting that quality of the two employees' performances is similar.

# ## Analyzing Sales by Country
# 
# Next, we can examine country-specific metrics, specifically total customers, total sales, average value of sales per customer, and average order value. Countries with only a single customer will be grouped into an 'Other' category.

# In[5]:


get_ipython().run_cell_magic('sql', '', '\nWITH country_data AS (\n    SELECT\n        c.customer_id,\n        i.total,\n        i.invoice_id,\n        CASE\n            WHEN \n                (SELECT COUNT(*) \n                 FROM customer \n                 WHERE country = c.country) = 1\n            THEN "Other"\n            ELSE c.country\n            END\n            AS country\n    FROM customer c\n    INNER JOIN invoice i ON c.customer_id = i.customer_id\n    )\n\nSELECT\n    country,\n    COUNT(DISTINCT(customer_id)) total_customers,\n    ROUND(SUM(total), 2) total_sales,\n    ROUND(SUM(total)/COUNT(DISTINCT(customer_id)), 2) sales_per_customer,\n    ROUND(SUM(total)/COUNT(invoice_id), 2) sales_per_order\nFROM \n    (\n    SELECT\n        cd.*,\n        CASE\n            WHEN cd.country = "Other" THEN 0\n            ELSE 1\n            END\n            AS sort\n    FROM country_data cd\n    )\nGROUP BY 1\nORDER BY sort DESC, total_sales DESC;')


# We find that the United States leads in total customers and sales. Based on the data, there may be opportunity for  market entry or increased advertising in Czech Republic, United Kingdom and India, all of which feature high values for average sales per customer and average sales per order.

# ## Albums vs. Tracks
# 
# Finally, we can evaluate how individual tracks are purchased. The store does not let customers purchase a whole album, and then add individual tracks to that same purchase (unless they do so by choosing each track manually). When customers purchase albums, they are charged the same price as if they had purchased each of those tracks separately.
# 
# Management is currently considering changing their purchasing strategy to save money. The strategy under consideration is to purchase only the most popular tracks from each album from record companies, instead of purchasing every track from an album.
# 
# We will explore what percentage of purchases are individual tracks vs whole albums, so that management can use this data to understand the effect this decision might have on overall revenue.
# 
# In order to answer the question, we'll have to identify whether each invoice has all the tracks from an album. We can do this by getting the list of tracks from an invoice and comparing it to the list of tracks from an album. We can then find the album to compare the purchase to by looking up the album that one of the purchased tracks belongs to. It doesn't matter which track we pick, since if it's an album purchase, that album will be the same for all tracks.
# 
# We can use the `EXCEPT` operator wrapped in a `CASE` statement to create a new column that evaluates whether or not each invoice was an album purchase. Summing the binary totals of this column will reveal the desired table of data.

# In[6]:


get_ipython().run_cell_magic('sql', '', 'WITH first_track_invoice AS (\n    SELECT \n        il.invoice_id invoice_id,\n        MIN(track_id) first_track\n        \n    FROM invoice_line il\n    GROUP BY 1\n    )\nSELECT \n    album_purchase,\n    COUNT(invoice_id) invoices,\n    ROUND(CAST(COUNT(invoice_id) AS FLOAT)/ (SELECT COUNT(*) FROM invoice), 3) pct\n    \n    FROM (\n        SELECT\n            fti.*,\n            CASE\n                WHEN (\n                    SELECT t.track_id\n                    FROM track t\n                    WHERE t.album_id = (SELECT t2.album_id FROM track t2\n                                        WHERE t2.track_id = fti.first_track)\n                    \n                    EXCEPT\n                    \n                    SELECT il2.track_id FROM invoice_line il2\n                    WHERE il2.invoice_id = fti.invoice_id \n                    ) IS NULL\n                AND\n                    (\n                    SELECT il2.track_id FROM invoice_line il2\n                    WHERE il2.invoice_id = fti.invoice_id\n                    \n                    \n                    EXCEPT\n        \n                    SELECT t.track_id FROM track t\n                    WHERE t.album_id = (\n                        SELECT t2.album_id FROM track t2\n                        WHERE t2.track_id = fti.first_track)\n                    ) IS NULL\n        \n            THEN "Yes"\n            ELSE "No"\n            END\n            AS "album_purchase"\n        FROM first_track_invoice fti\n        )\nGROUP BY 1;')


# This data reveals that album purchases account for 18.6% of all purchased tracks, nearly a fifth of all revenue. Based on these findings, we can recommend that the company avoid purchasing only select tracks from albums, since that could result in a loss of one fifth of revenue.

# ## Conclusion
# 
# In this project, we have addressed a number of business questions using SQL queries and joins. We reached the following conclusions, to be recommended to the company:
#    * The company should purchase Pop, Punk, and Blues albums and be on the lookout for opportunities to purchase more Rock albums, as the Rock genre accounts for over half of all purchases.
#    * The company does most of its business in the United States, but new opportunities for growth could be present in Czech Republic, United Kingdom, and India.
#    * There is not an appreciable difference in the overall quality of sales employee performance.
#    * The company should refrain from changing its purchasing policy to one that buys only certain tracks from albums. Doing so risks losing ~20% of total revenue. 
