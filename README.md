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
Note: This uses up to 40GB of RAM (Would use more, but currently dropping data that 
4. Start the neo4j docker container
```
docker run \
--publish=127.0.0.1:7474:7474 \
--publish=127.0.0.1:7687:7687 \
--user="$(id -u):$(id -g)" \
--volume=$HOME/neo4j/rxnorm/data:/data \
--volume=$HOME/neo4j/import:/var/lib/neo4j/import \
--env NEO4J_server_default__listen__address=0.0.0.0 \
-d neo4j
```
5. Run the data fill db script (THIS WILL DELETE ALL CURRENT DATA IN '$HOME/neo4j/rxnorm/data')
`bash fill_db.sh`
6. Start the webapp
`python3 webapp.py`
7. Browse to the localhost web page
[RxNorm WebApp](https://localhost:8088)

