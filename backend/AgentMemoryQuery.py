import os
from flask import Flask
from models import db, AgentMemory
from dotenv import load_dotenv

load_dotenv()

# Load the database URI from the environment variable
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("No DATABASE_URL environment variable set")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
db.init_app(app)

def get_agent_memory_by_id(memory_id: int):
    with app.app_context():
        # Query the AgentMemory table for the entry with the specified ID
        memory_entry = AgentMemory.query.get(memory_id)
        
        if memory_entry:
            # Convert the entry to a dictionary
            return memory_entry.to_dict()
        else:
            return None

if __name__ == "__main__":
    # Get the ID from user input
    memory_id = int(input("Enter the ID of the AgentMemory entry: "))
    
    # Fetch the memory entry
    memory_dict = get_agent_memory_by_id(memory_id)
    
    if memory_dict:
        print(memory_dict)
    else:
        print(f"No entry found with ID {memory_id}")