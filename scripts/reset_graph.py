"""Drop all nodes and relationships — use with caution!"""
from graph.loaders.neo4j_client import Neo4jClient

if __name__ == "__main__":
    confirm = input("This will delete ALL graph data. Type 'yes' to continue: ")
    if confirm == "yes":
        with Neo4jClient() as client:
            client.run("MATCH (n) DETACH DELETE n")
        print("🗑️  Graph cleared.")
