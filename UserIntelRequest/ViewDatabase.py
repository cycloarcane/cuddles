import curses
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

def list_documents(stdscr, client, collection_name):
    collection_name = collection_name.lower().replace(' ', '_')
    collection = client.get_collection(name=collection_name)

    documents = collection.get(include=["documents", "metadatas"])
    row = 2

    stdscr.clear()
    stdscr.addstr(0, 0, f"Documents in collection: {collection_name}\n")

    for i in range(len(documents["documents"])):
        if row >= curses.LINES - 2:
            stdscr.addstr(curses.LINES - 1, 0, "Press any key to see more...")
            stdscr.refresh()
            stdscr.getch()
            stdscr.clear()
            stdscr.addstr(0, 0, f"Documents in collection: {collection_name}\n")
            row = 2

        stdscr.addstr(row, 0, f"ID: {i}")
        row += 1
        stdscr.addstr(row, 0, f"Document: {documents['documents'][i]}")
        row += 1
        stdscr.addstr(row, 0, f"Metadata: {documents['metadatas'][i]}")
        row += 1
        stdscr.addstr(row, 0, "-" * 50)
        row += 1

    stdscr.addstr(curses.LINES - 1, 0, "Press any key to exit...")
    stdscr.refresh()
    stdscr.getch()

def get_collections(client):
    collections = client.list_collections()
    return [col.name for col in collections]

def display_menu(stdscr, collections):
    curses.curs_set(0)
    stdscr.clear()
    stdscr.refresh()

    current_row = 0

    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "VIEW DATABASE")
        for idx, row in enumerate(collections):
            if idx == current_row:
                stdscr.addstr(idx + 1, 0, f"> {row}", curses.A_REVERSE)
            else:
                stdscr.addstr(idx + 1, 0, row)
        
        key = stdscr.getch()

        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(collections) - 1:
            current_row += 1
        elif key == curses.KEY_ENTER or key in [10, 13]:
            return collections[current_row]
        elif key in [27, ord('q')]:  # ESC or 'q' to exit
            return None

        stdscr.refresh()

def main(stdscr):
    stdscr.clear()
    stdscr.addstr(0, 0, cuddles_art())
    stdscr.refresh()

    client = chromadb.PersistentClient(path="./data")
    collections = get_collections(client)

    if not collections:
        stdscr.addstr(1, 0, "No collections found.")
        stdscr.refresh()
        stdscr.getch()
        return

    selected_collection = display_menu(stdscr, collections)

    if selected_collection is not None:
        stdscr.clear()
        stdscr.addstr(0, 0, f"Documents in collection: {selected_collection}")
        stdscr.refresh()
        list_documents(stdscr, client, selected_collection)

if __name__ == "__main__":
    curses.wrapper(main)