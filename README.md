# DSE241-Visualization
## Final Project
## Chris Armstrong - 2023-03-24

## Files
1. generate_neo4j_data.py - script to create CSV files that Neo4j can ingest
1.1 rxnorm/graph.py       - Module supporting the script to genreate Neo4j datasets
2. fill_db.sh             - Script that connects to a running Neo4j Docker Instance clears the DB and loads the new data
    ! - This script WILL DELETE all your bases, and your Neo4j database too.
3. webapp.py              - Web application that is suppored by the Neo4j database
4. static/index.html      - Website main page with Javascript to leverage D3js support for showing Neo4j data in the browser
