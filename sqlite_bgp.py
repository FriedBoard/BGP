# This script can be used to split raw bgp routing table entries into a view of the resulting routes based on the shortest path.
# Author: Leroy van der Steenhoven

# import sqlite3, and os.path
import sqlite3
import os.path
from os import path

# Link-local address for the next-hop attribute
next_Hop = 'fe80::215:5dff:fe14:7c05'
# Set how many announcements you want per bgp.txt, this is to prevent a ExaBGP process from freezing
announcement_Limit = 5000

# Create and connect to an in-memory database and disk backed database
conn = sqlite3.connect(':memory:')
conn2 = sqlite3.connect('bgp2.db')

# Function to create the bgp.db sqlite database with table bgp_Table (All paths) and route_Table (Best paths)
def create_Database():
    # Create the bgp_Table
    print('Creating bgp_Table')
    conn.execute('''CREATE TABLE bgp_Table (prefix text, path text)
                ''')

    # Create route table
    conn.execute('''CREATE TABLE route_Table (prefix text, path text, prefix_Length text, path_Length text)  ''')

    # Open the bgptable.txt file
    bgp_Table = open('bgptable.txt', 'r')

    # Create a list with a list for every row in it, sourced from: https://stackoverflow.com/questions/16922214/reading-a-text-file-and-splitting-it-into-single-words-in-python
    bgp_Table_List = [row.split() for row in bgp_Table]

    print('Entering prefixes and paths')
    # Loop through the list of lists and add prefixes to the tuple. Because it's tuple all prefixes will be unique at the end.
    for prefix_Entry in bgp_Table_List:
        # Get the prefix
        prefix = prefix_Entry[0]

        # Remove the prefix from the list
        prefix_Entry.pop(0)

        # Create path, sourced from: https://stackoverflow.com/questions/5618878/how-to-convert-list-to-string
        path = ' '.join(str(x) for x in prefix_Entry)

        # Insert the path into the bgp_Table
        query = '''INSERT INTO bgp_Table VALUES ('{}', '{}')'''.format(prefix, path)
        conn.execute(query)

        
    print('Creating prefix index for bgp_Table')
    # Create a indexes for faster execution next run
    query = ''' CREATE index idx_bgp_Table_prefix ON bgp_Table (prefix); '''
    conn.execute(query)
    
    # Save data
    conn.commit()

# Function that returns the best path for a list of paths assuming it's all for the same prefix.
def best_Path(paths):
    # Reference length
    length = 1000
    
    # For every tuple (path) in the list (paths)
    for path in paths:
        # Make it a list so that it's mutable
        path = list(path)
        
        # Split the ASNs to a list
        path[1] = path[1].split(' ')
        
        path_Length = len(path[1])

        if path_Length < length:
            shortest_Path = path
            length = path_Length

    # Return the shortest path and length, the first shortest path is considered the best path in this script to decrease complexity, computing power requirements and certain information for proper path consideration like neighborship duration is lacking in the dataset.
    return(shortest_Path, length)

# Create a database for faster processing.
create_Database()
print('Memory DB created')

# Query the database for unique prefixes ordered most paths to least paths for more efficient processing later
query = "SELECT prefix FROM bgp_Table GROUP BY prefix ORDER BY count(path) DESC"
unique_Prefixes = conn.execute(query).fetchall()

# Print how many unique prefixes are available
print(str(len(unique_Prefixes)) + ' Unique prefixes available in this dataset.')

print('Calculating best path for every unique prefix')

# Start gathering the shortest paths
for prefix in unique_Prefixes:
    # Get all unique paths for that prefix from the database, this avoids processing a path twice.
    query = '''SELECT distinct * FROM bgp_Table WHERE PREFIX='{}' '''.format(prefix[0])
        
    # Get the results, it returns a list with tuples like so: [(prefix, path), (prefix, path)] 
    paths = conn.execute(query).fetchall()

    # Figure out what the shortest path is
    shortest_Path = best_Path(paths)

    # Create the query with the prefix located at [0][0], shortest path located at [0][1], prefix lenght located at [1] when [0][0] (prefix) is split by /. Also add the path length located at [1].
    conn.execute('''INSERT INTO route_Table VALUES ('{}', '{}', '{}', '{}') '''.format(shortest_Path[0][0], ' '.join(shortest_Path[0][1]), shortest_Path[0][0].split('/')[1], shortest_Path[1]))

# Create an index on path in route_Table for more speed later
query = ''' CREATE index idx_route_Table_Path ON route_Table (path); '''
conn.execute(query)

# Close and save database
conn.commit()

print('Creating file copy of in-memory database')

# Dump the memory database to disk for review if it doesn't exist yet
for row in conn.iterdump():
    if row not in ('BEGIN;', 'COMMIT;'):
        conn2.execute(row)
conn2.commit()

# Get unique paths
query = ''' SELECT DISTINCT path FROM route_Table '''
route_Paths = conn.execute(query).fetchall()

# Ticker value for announcements per bgp.txt
ticker = 0
file_Ticker = 0
bgp_Txt = 'bgp_{}.txt'.format(str(file_Ticker))
text_File = open(bgp_Txt,'a')

print('Creating bgp.txt files')
print(bgp_Txt + ' Created')

for route_Path in route_Paths:
    # Get the attached prefixes
    query = ''' SELECT prefix FROM route_Table WHERE path='{}' '''.format(route_Path[0])
    path_Prefixes = conn.execute(query).fetchall()
    text = "'announce attribute next-hop {} as-path [ {} ] nlri {} ',".format(next_Hop, route_Path[0], ' '.join(str(x[0]) for x in path_Prefixes))
    text_File.write(text)

    # Measures to limit the amount of announcements per bgp_Txt
    ticker = ticker + 1
    if ticker == announcement_Limit:
        file_Ticker = file_Ticker + 1
        bgp_Txt = 'bgp_{}.txt'.format(str(file_Ticker))
        print(bgp_Txt + ' Created')
        text_File = open(bgp_Txt, 'a')
        ticker = 0


# Close the connections
conn.close()
conn2.close()

print('Done')