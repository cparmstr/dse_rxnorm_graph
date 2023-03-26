import logging
import os
#!/usr/bin/env python
from json import dumps

from flask import Flask, Response, g, request

from neo4j import GraphDatabase, basic_auth

app = Flask(__name__, static_url_path="/static/")

url = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
username = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "neo4j")
neo4j_version = os.getenv("NEO4J_VERSION", "5")
database = os.getenv("NEO4J_DATABASE", "neo4j")

port = os.getenv("PORT", 8088)

driver = GraphDatabase.driver(url, auth=basic_auth(username, password))
print("Connected?", driver.verify_connectivity())


def get_db():
    if not hasattr(g, "neo4j_db"):
        g.neo4j_db = driver.session(database=database)
    return g.neo4j_db


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, "neo4j_db"):
        g.neo4j_db.close()


@app.route("/")
def get_index():
    return app.send_static_file("index.html")


@app.route("/search")
def get_search():
    def work(tx, q_):
        return list(
            tx.run(
                "MATCH (n:NDC)-[:aka]-(i) "
                "WHERE n.ndc CONTAINS $ndc1"
                " AND n.brand IS NOT NULL "
                " AND i.brand IS NOT NULL "
                "RETURN n.ndc as ndc, n.brand as brand "
                "LIMIT 7",
                {"ndc1": q_},
            )
        )

    try:
        q = request.args["q"]
    except KeyError:
        return []
    else:
        db = get_db()
        results = db.execute_read(work, q)
        print(results)
        return Response(
            dumps({"ndc": results}),
            mimetype="application/json",
        )


@app.route("/ingredients/<ndc>")
def get_ingredients(ndc):
    def work(tx, ndc_):
        return list(
            tx.run(
                "MATCH (n:NDC {ndc:$ndc})-[*1..3]-(i:IN)"
                "WHERE i.brand IS NOT NULL "
                "RETURN COLLECT(DISTINCT i.brand) as ingredients",
                {"ndc": ndc_},
            )
        )

    db = get_db()
    results = db.execute_read(work, ndc)

    return Response(
        dumps({"ingredients": results}),
        mimetype="application/json",
    )


@app.route("/graph")
def get_graph():
    def work(tx, limit):
        return list(
            tx.run(
                "MATCH (n:NDC)-[:aka]-(v)-[*1..2]-(i:IN) "
                "WHERE n.brand IS NOT NULL and i.brand IS NOT NULL AND v.brand IS NOT NULL "
                "RETURN n.ndc as ndc, n.brand as brand, n.rxcui as rxcui, collect(DISTINCT i) as ingredients "
                "LIMIT $limit ",
                {"limit": limit},
            )
        )

    db = get_db()
    results = db.execute_read(work, request.args.get("limit", 700))
    nodes = []
    rels = []
    i = 0
    for record in results:
        node_data = {
            "ndc": record["ndc"],
            "name": record["brand"],
            "label": "NDC",
            "rxcui": record["rxcui"],
            "icount": len(record["ingredients"]),
        }
        nodes.append(node_data)
        target = i
        i += 1
        for ingredient in record["ingredients"]:
            ingredient = {
                "name": ingredient["brand"],
                "label": "IN",
                "rxcui": ingredient["rxcui"],
                "icount": 0,
            }
            try:
                source = nodes.index(ingredient)
            except ValueError:
                nodes.append(ingredient)
                source = i
                i += 1
            rels.append({"source": source, "target": target})
    return Response(dumps({"nodes": nodes, "links": rels}), mimetype="application/json")


# https://github.com/neo4j-examples/movies-python-bolt/blob/main/movies_async.py

if __name__ == "__main__":
    logging.root.setLevel(logging.INFO)
    logging.info("Starting on port %d, database is at %s", port, url)
    app.run(port=port)
