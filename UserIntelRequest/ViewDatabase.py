from rich.console import Console
from rich.table import Table
import chromadb

def cuddles_art():
    art = """
██████   █████  ████████  █████  ██████   █████  ███████ ███████     ██    ██ ██ ███████ ██     ██     
██   ██ ██   ██    ██    ██   ██ ██   ██ ██   ██ ██      ██          ██    ██ ██ ██      ██     ██     
██   ██ ███████    ██    ███████ ██████  ███████ ███████ █████       ██    ██ ██ █████   ██  █  ██     
██   ██ ██   ██    ██    ██   ██ ██   ██ ██   ██      ██ ██           ██  ██  ██ ██      ██ ███ ██     
██████  ██   ██    ██    ██   ██ ██████  ██   ██ ███████ ███████       ████   ██ ███████  ███ ███      
                                                                                                       
                                                                                                                                  
"""
    return art

def list_documents(console, client, collection_name):
    collection_name = collection_name.lower().replace(' ', '_')
    collection = client.get_collection(name=collection_name)
    documents = collection.get(include=["documents", "metadatas"])

    table = Table(title=f"Documents in collection: {collection_name}")
    table.add_column("ID", justify="center")
    table.add_column("Document", justify="center")
    table.add_column("Metadata", justify="center")

    for i in range(len(documents["documents"])):
        table.add_row(str(i), documents["documents"][i], str(documents["metadatas"][i]))

    console.print(table)

def get_collections(client):
    collections = client.list_collections()
    return [col.name for col in collections]

def display_menu(console, collections):
    console.print("VIEW DATABASE", style="bold")
    for idx, collection in enumerate(collections):
        console.print(f"[{idx}] {collection}")

    while True:
        choice = console.input("\nSelect a collection (or type 'exit' to quit): ")
        if choice.isdigit() and int(choice) < len(collections):
            return collections[int(choice)]
        elif choice.lower() == 'exit':
            return None
        else:
            console.print("Invalid selection. Please try again.")

def main():
    console = Console()
    console.print(cuddles_art(), style="bold cyan")

    client = chromadb.PersistentClient(path="./data")
    collections = get_collections(client)

    if not collections:
        console.print("No collections found.", style="bold red")
        return

    selected_collection = display_menu(console, collections)

    if selected_collection is not None:
        list_documents(console, client, selected_collection)

if __name__ == "__main__":
    main()
