# BGP
This repository contains my work for investigating the impact of the layer 2 MTU on modern day BIRD route servers. 

## General

The sqlite_bgp.py script can be used to generate announcement messages for ExaBGP based on a bgp table "dump" in text format that contains a prefix and a path. It also creates a sqlite database so that one can manually query for certain statistics like prefix lengths and path lengts.

### sqlite_bgp.py explained

sqlite_bgp.py will take a bgp_table_txt (bgptable.txt by default) as input. From this input it will create an sqlite database in-memory (later dumped to disk as bgp_routes.db) which it will fill with all routes/paths from the intput txt file. These routes/paths are placed in bgp_Table. 

After populating bgp_Table it will select the best path for each unique prefix in the bgp_Table. The best path criteria are: the shortest path and if there is a tie it will take the first path. This prefix/path combo is than placed in route_Table. This table also includes columns for prefix lenght and path length.

After the best path selection is done for all unique prefixes it will create bgp_{number}.txt files containing announcements for ExaBGP. These files are limited to announcement_Limit amount announcements. This is done to prevent ExaBGP from freezing at some point. 

### ExaBGP setup
route_{number}.py contains examples of processes that can be used to insert the annoucements to ExaBGP.

exabgp.conf contains an example of the exabgp configuration to run multiple processes.

Make sure you use group-updates in the neighbor configuration. If this is not set announcements will be send as independent bgp update messages/packets. When group-updates is set and supported by the receiving end multiple bgp updates are put in one packet improving efficiency.

## Sources:
The routes found in route_x.py are sourced from: http://bgp.potaroo.net/v6/as6447/bgptable.txt this data was used for testing as well.
