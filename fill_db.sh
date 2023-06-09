#!/bin/bash
# Script erases the entire DB!!!
set -e

original_import_dir="import"
neo4j_home="$HOME/neo4j"
neo4j_data="${neo4j_home}/data"
neo4j_import="${neo4j_home}/import"

echo "Dropping all Neo4j data in $neo4j_data!!!"
echo
echo "Do you mean to drop the Neo4j database?"
read -p "Type 'drop' to continue. " continue_to_drop
if [[ ! "$continue_to_drop" == "drop" ]]; then
  exit 1
fi

container=$(docker ps --format json | jq -r '{id: .ID, img: .Image} | select(.img == "neo4j") | .id')
if [[ ! -z $container ]]; then
  echo "Stopping Neo4j..."
  docker stop $container 
fi
sudo rm -rf "${neo4j_data}/databases/*"
sudo rm -rf "${neo4j_data}/transactions/*"
echo "Removed old databases"

# Remove old files and copy new ones into the Neo4j import folder for the Docker container
sudo rm -rf "$neo4j_import/*"
mkdir -p "$neo4j_import"
cp ./$original_import_dir/*.csv* "$neo4j_import"
echo "Copied files for import into Neo4j"

# Let file locks settle before starting Docker Neo4j import tool
sleep 1

docker run -it \
--user="$(id -u):$(id -g)" \
--volume="$neo4j_data:/data" \
--volume="$neo4j_import:/var/lib/neo4j/import" \
neo4j bash -c 'neo4j-admin database import full \
--nodes=import/ndc_nodes.csv \
--nodes=import/rxcui_BN_nodes.csv \
--nodes=import/rxcui_IN_nodes.csv \
--nodes=import/rxcui_SBD_nodes.csv \
--nodes=import/rxcui_SBDC_nodes.csv \
--nodes=import/rxcui_SBDF_nodes.csv \
--nodes=import/rxcui_SBDG_nodes.csv \
--nodes=import/rxcui_SCD_nodes.csv \
--nodes=import/rxcui_SCDC_nodes.csv \
--nodes=import/rxcui_SCDF_nodes.csv \
--nodes=import/rxcui_SCDG_nodes.csv \
--nodes=import/tui_semantic_types_nodes.csv \
--relationships=import/ndc_cui_relations.csv \
--relationships=import/rel_consists_of.csv \
--relationships=import/rel_contains.csv \
--relationships=import/rel_has_ingredient.csv \
--relationships=import/rel_has_tradename.csv \
--skip-bad-relationships=true \
--overwrite-destination'

echo "Import Completed"
sleep 4 # Give Docker container time to shutdown properly

# Start Neo4j Server
docker run \
--publish=127.0.0.1:7474:7474 \
--publish=127.0.0.1:7687:7687 \
--user="$(id -u):$(id -g)" \
--volume="$neo4j_data:/data" \
--volume="$neo4j_import:/var/lib/neo4j/import" \
--env NEO4J_server_default__listen__address=0.0.0.0 \
-d neo4j
# --env NEO4JLABS_PLUGINS='["graph-data-science"]' \ #Add this to include Data Science Modules

sleep 3
echo "Ready!"
sleep 2
echo "Set!"
sleep 1
echo "DSE241!"
echo "Log in to Neo4j here http://localhost:7474/browser"
echo "Username and password are both: 'neo4j'"

# Got TLS? 
# final_container=$(docker run \
# --publish=127.0.0.1:7473:7473 \
# --publish=127.0.0.1:7687:7687 \
# --user="$(id -u):$(id -g)" \
# --volume=$HOME/neo4j/certificates/ssl:/ssl \
# --volume=$HOME/neo4j/rxnorm/data:/data \
# --volume=$HOME/neo4j/import:/var/lib/neo4j/import \
# --env NEO4J_server_https_enabled=true \
# --env NEO4J_dbms_ssl_policy_https_enabled=true \
# --env NEO4J_dbms_ssl_policy_https_tls__versions=TLSv1.3 \
# --env NEO4J_dbms_ssl_policy_https_base__directory=/ssl/https \
# --env NEO4J_server_default__listen__address=0.0.0.0 \
# --env NEO4J_server_bolt_tls__level=REQUIRED \
# --env NEO4J_dbms_ssl_policy_bolt_enabled=true \
# --env NEO4J_dbms_ssl_policy_bolt_tls__versions=TLSv1.3 \
# --env NEO4J_dbms_ssl_policy_bolt_base__directory=/ssl/bolt \
# -d neo4j)
