#!/bin/bash
# Script erases the entire DB!!!

set -e

container=$(docker ps --format json | jq -r '{id: .ID, img: .Image} | select(.img == "neo4j") | .id')
if [[ ! -z $container ]]; then
  docker stop $container 
fi
sudo rm  -rf $HOME/neo4j/rxnorm/data/databases/*
sudo rm  -rf $HOME/neo4j/rxnorm/data/transactions/*

sudo rm -rf $HOME/neo4j/import/*
cp *.csv* $HOME/neo4j/import/

new_container=$(docker run \
--publish=127.0.0.1:7474:7474 \
--publish=127.0.0.1:7687:7687 \
--user="$(id -u):$(id -g)" \
--volume=$HOME/neo4j/rxnorm/data:/data \
--volume=$HOME/neo4j/import:/var/lib/neo4j/import \
--env NEO4J_server_default__listen__address=0.0.0.0 \
-d neo4j)

docker exec -it $new_container \
bash -c 'neo4j-admin database import full \
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
--overwrite-destination \
neo4j'

echo "Import Completed"
sleep 3
docker stop $new_container

final_container=$(docker run \
--publish=127.0.0.1:7474:7474 \
--publish=127.0.0.1:7687:7687 \
--user="$(id -u):$(id -g)" \
--volume=$HOME/neo4j/rxnorm/data:/data \
--volume=$HOME/neo4j/import:/var/lib/neo4j/import \
--env NEO4J_server_default__listen__address=0.0.0.0 \
--env NEO4JLABS_PLUGINS='["graph-data-science"]' \
-d neo4j)

sleep 3
echo "Ready!"
sleep 3
echo "Set!"
sleep 3
echo "DSE241!"
echo "Log in to Neo4j here http://localhost:7474/browser"
echo "username and password: 'neo4j'"

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
