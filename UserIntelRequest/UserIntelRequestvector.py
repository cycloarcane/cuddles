import chromadb

def cuddles_art():
    art = """
 ██████ ██    ██ ██████  ██████  ██      ███████ ███████     
██      ██    ██ ██   ██ ██   ██ ██      ██      ██          
██      ██    ██ ██   ██ ██   ██ ██      █████   ███████     
██      ██    ██ ██   ██ ██   ██ ██      ██           ██     
 ██████  ██████  ██████  ██████  ███████ ███████ ███████     
                                                             
                                                                                      
"""
    return art
#art font is ANSI Regular
def get_user_input(prompt):
    response = input(prompt)
    return response if response else "Not provided"

def initialize_chromadb(client, collection_name):
    # Ensure the collection name meets ChromaDB's naming restrictions
    collection_name = collection_name.lower().replace(' ', '_')
    collection = client.get_or_create_collection(name=collection_name)
    return collection

def save_to_chromadb(collection, data):
    documents = [f"{key}: {value}" for key, value in data.items() if value != "Not provided"]
    ids = [f"{data.get('Organisation name', 'unknown')}_{i}" for i in range(len(documents))]
    collection.add(
        documents=documents,
        ids=ids
    )

def main():
    print(cuddles_art())
    print("Welcome to cuddles. Please provide information about the target.")
    print("If you don't have a piece of information simply press return for the next question.")
    print("You must enter an organisation name:")

    questions = {
        "Organisation name": "Please enter the organisation name: ",
        "Known domains and IPs": "Please enter known domains and IPs separated by commas: ",
        "Known email addresses": "Please enter known email addresses separated by commas: ",
        "Known credentials": "Please enter known credentials (e.g., annie94:superpassword) separated by commas: ",
        "Known names of members": "Please enter known names of members: ",
        "Known technologies": "Please enter known technologies being used by the organisation: ",
        "Known repository URLs": "Please enter known repository URLs for git or similar: ",
        "Any other useful information": "Please enter any other known useful information: "
    }

    responses = {}

    for key, question in questions.items():
        responses[key] = get_user_input(question)

    org_name = responses["Organisation name"]

    if org_name == "Not provided":
        print("Organisation name is required. Exiting.")
        return

    # Initialize ChromaDB client and get the collection
    client = chromadb.PersistentClient(path="./data")
    collection = initialize_chromadb(client, org_name)

    # Save to ChromaDB
    save_to_chromadb(collection, responses)

    print(f"Information saved to the database under collection '{org_name}'")

if __name__ == "__main__":
    main()