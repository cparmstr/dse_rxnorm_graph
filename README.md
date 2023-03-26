# DSE241-Visualization
## Final Project
## Chris Armstrong - 2023-03-24

## Files
1. generate_neo4j_data.py - script to create CSV files that Neo4j can ingest
   - rxnorm/graph.py       - Module supporting node and relationship CSV creation
   - rxnorm/rrf.py         - Module supporting data transformations
2. fill_db.sh             - Script that connects to a running Neo4j Docker Instance clears the DB and loads the new data
    ! - This script WILL DELETE all your bases, and your Neo4j database too.
3. webapp.py              - Web application that is suppored by the Neo4j database
4. static/index.html      - Website main page with Javascript to leverage D3js support for showing Neo4j data in the browser
5. neo4j (folder)         - Database supporting the webapp and interactive UI

## Data & Location
This uses the full monthly release dataset:
### Main Link to RxNorm Files 
- https://www.nlm.nih.gov/research/umls/rxnorm/docs/rxnormfiles.html
### Direct
- https://download.nlm.nih.gov/umls/kss/rxnorm/RxNorm_full_03062023.zip

## Usage
This package requiers Docker. The set of scripts and webapp are in the order that they should run if starting from scratch.
1. Download the data from the link above and unzip it into an "rxnorm" folder
2. Install python dependencies from requirements.txt
`pip install -r requirements.txt`
3. Run the "generate_neo4j_data.py" script
`python3 generate_neo4j_data.py`
Note: This uses a lot of RAM
4. Run the data fill db script (THIS WILL DELETE ALL CURRENT DATA IN '$HOME/neo4j/rxnorm/data')
`bash fill_db.sh`
5. Browse to the Neo4J server site and set a new password: [Neo4j Localhost](http://localhost:7474)
6. Set an environment variable so the webapp can use your new DB password.
`export NEO4J_PASSWORD='<password_goes_here>'`
7. Start the webapp
`python3 webapp.py`
8. Browse to the localhost web page [RxNorm WebApp](http://localhost:8088)
9. Search for an NDC or click a node in the graph to see it's ingredients

