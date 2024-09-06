import re
import sqlite3
import os
from openai import OpenAI
import curses
import subprocess
client = OpenAI()
import shutil

# Set your OpenAI API key here
OpenAI.api_key = os.getenv('OPENAI_API_KEY', 'your-openai-api-key')

def clean_search_term(term):
    # Remove unwanted characters like backticks, asterisks, etc.
    return term.replace('`', '').replace('*', '').replace('-', '').strip()

# 1. Validate user input for IP address and project name
def is_valid_ip(ip_address):
    ip_pattern = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")
    return ip_pattern.match(ip_address) is not None

def run_nmap_scan(ip_address):
    command = f"nmap {ip_address} -sC -sV"
    result = subprocess.run(command.split(), capture_output=True, text=True)
    return result.stdout

def is_valid_project_name(project_name):
    return project_name.isalnum()

def get_user_input():
    ip_address = input("Enter the IP address: ")
    project_name = input("Enter the project name: ")

    if not is_valid_ip(ip_address):
        print("Invalid IP address format. Please try again.")
        return get_user_input()

    if not is_valid_project_name(project_name):
        print("Invalid project name. It must not contain special characters.")
        return get_user_input()

    return ip_address, project_name

# 2. Set up the SQLite database
def setup_database():
    conn = sqlite3.connect('projects.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY,
            project_name TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            scan_results TEXT
        )
    ''')
    conn.commit()
    conn.close()

def store_ip(ip_address, project_name):
    conn = sqlite3.connect('projects.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO projects (project_name, ip_address) VALUES (?, ?)
    ''', (project_name, ip_address))
    conn.commit()
    conn.close()

# 3. Retrieve the IP address and run an Nmap scan
def get_ip_from_db(project_name):
    conn = sqlite3.connect('projects.db')
    cursor = conn.cursor()
    cursor.execute('SELECT ip_address FROM projects WHERE project_name = ?', (project_name,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# def run_nmap_scan(ip_address):
#     command = f"nmap {ip_address} -sC -sV"
#     os.system(command)
#     return command

# 4. Store Nmap results to the database
def store_nmap_results(project_name, scan_results):
    conn = sqlite3.connect('projects.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE projects SET scan_results = ? WHERE project_name = ?
    ''', (scan_results, project_name))
    conn.commit()
    conn.close()

# 5. Analyze scan results using OpenAI GPT-4o-mini with the template
def retrieve_scan_results(project_name):
    conn = sqlite3.connect('projects.db')
    cursor = conn.cursor()
    cursor.execute('SELECT scan_results FROM projects WHERE project_name = ?', (project_name,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def analyze_scan_results(scan_results):
    prompt = f"Analyze the following nmap scan results and provide feedback on potential vulnerabilities: {scan_results}"
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000
        )
        analysis = response.choices[0].message.content.strip()
        print(f"Analysis: {analysis}")
        return analysis
    except Exception as e:
        raise Exception(f"Error analyzing scan results with LLM: {str(e)}")

# 6. Generate searchsploit terms based on scan results using the template
def generate_searchsploit_terms(scan_results):
    prompt = f"Generate searchsploit search terms based on the following nmap scan results, but keep it to one word possibly with the version as searchsploit is very specific. For example 'ftp 1.2' or just 'ftp'. Don't add numbers or list formatting: {scan_results}"
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000
        )
        search_terms = response.choices[0].message.content.strip()
        print(f"Searchsploit Terms: {search_terms}")
        return search_terms
    except Exception as e:
        raise Exception(f"Error generating searchsploit terms with LLM: {str(e)}")


def modify_exploit(exploit_path):
    modified_exploits_dir = os.path.expanduser('./modified_exploits')
    os.makedirs(modified_exploits_dir, exist_ok=True)

    new_path = os.path.join(modified_exploits_dir, os.path.basename(exploit_path))
    shutil.copy2(exploit_path, new_path)

    print(f"Copied exploit to: {new_path}")

    with open(new_path, 'r') as file:
        content = file.read()

    prompt = f"Suggest modifications for the following exploit code to make it more effective or customized:\n\n{content}"
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000
        )
        suggestions = response.choices[0].message.content.strip()
        print(f"Suggested modifications:\n{suggestions}")

        with open(new_path, 'w') as file:
            file.write(f"# Original code:\n{content}\n\n# Suggested modifications:\n{suggestions}")

        print(f"Modified exploit saved to: {new_path}")
    except Exception as e:
        print(f"Error generating modifications: {str(e)}")

def show_search_terms(terms):
    def navigate_menu(stdscr):
        curses.curs_set(0)
        current_row = 0

        while True:
            stdscr.clear()
            for idx, term in enumerate(terms):
                x = 0
                y = idx
                if idx == current_row:
                    stdscr.attron(curses.color_pair(1))
                    stdscr.addstr(y, x, term)
                    stdscr.attroff(curses.color_pair(1))
                else:
                    stdscr.addstr(y, x, term)
            stdscr.refresh()

            key = stdscr.getch()

            if key == curses.KEY_UP and current_row > 0:
                current_row -= 1
            elif key == curses.KEY_DOWN and current_row < len(terms) - 1:
                current_row += 1
            elif key in [10, 13]:  # Enter key is pressed
                break  # Exit the loop once a term is selected

        return terms[current_row]

    selected_term = curses.wrapper(navigate_menu)
    print(f"Original selected search term: {selected_term}")

    cleaned_term = clean_search_term(selected_term)
    print(f"Cleaned search term: {cleaned_term}")

    searchsploit_command = f"searchsploit \"{cleaned_term}\""

    print(f"Executing: {searchsploit_command}")

    try:
        result = subprocess.run(searchsploit_command, shell=True, capture_output=True, text=True)
        print(result.stdout)  # Print the output of the searchsploit command

        if result.returncode == 0:
            exploit_paths = parse_searchsploit_output(result.stdout)
            
            if exploit_paths:
                selected_exploit = select_exploit(exploit_paths)
                
                if selected_exploit:
                    modify_exploit(selected_exploit)
    except Exception as e:
        print(f"Error running searchsploit: {e}")

    return cleaned_term

def parse_searchsploit_output(output):
    exploit_paths = []
    for line in output.split('\n'):
        if '  ' in line:  # Exploits are typically indented
            path = line.split()[-1]
            if path.startswith('/usr/share/exploitdb/'):
                exploit_paths.append(path)
    return exploit_paths

def select_exploit(exploit_paths):
    def navigate_menu(stdscr):
        curses.curs_set(0)
        current_row = 0

        while True:
            stdscr.clear()
            for idx, path in enumerate(exploit_paths):
                x = 0
                y = idx
                if idx == current_row:
                    stdscr.attron(curses.color_pair(1))
                    stdscr.addstr(y, x, os.path.basename(path))
                    stdscr.attroff(curses.color_pair(1))
                else:
                    stdscr.addstr(y, x, os.path.basename(path))
            stdscr.refresh()

            key = stdscr.getch()

            if key == curses.KEY_UP and current_row > 0:
                current_row -= 1
            elif key == curses.KEY_DOWN and current_row < len(exploit_paths) - 1:
                current_row += 1
            elif key in [10, 13]:  # Enter key is pressed
                break

        return exploit_paths[current_row]

    return curses.wrapper(navigate_menu)
# Main program flow
if __name__ == "__main__":
    setup_database()

    # Step 1: Get IP and project name from user
    ip, project_name = get_user_input()

    # Step 2: Store the IP and project name in the database
    store_ip(ip, project_name)

    # Step 3: Retrieve IP and run nmap scan
    ip_address = get_ip_from_db(project_name)
    if ip_address:
        scan_command = run_nmap_scan(ip_address)
        scan_results = run_nmap_scan(ip_address)
        store_nmap_results(project_name, scan_results)

        # Step 4: Retrieve and analyze scan results
        scan_results = retrieve_scan_results(project_name)
        if scan_results:
            analysis = analyze_scan_results(scan_results)

            # Step 5: Generate searchsploit terms
            search_terms = generate_searchsploit_terms(scan_results)

            # Step 6: Display search terms in an interactive UI
            terms_list = search_terms.split('\n')
            show_search_terms(terms_list)
