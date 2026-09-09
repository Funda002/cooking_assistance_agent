class MemoryManager:

    def __init__(self):

        self.memory = {
            "conversation": [],
            "preferences": {},
            "facts": {}
        }

    # -----------------------------
    # Store Preference
    # -----------------------------

    def store_preference(self, key, value):

        self.memory["preferences"][key] = value

    # -----------------------------
    # Store Fact
    # -----------------------------

    def store_fact(self, key, value):

        self.memory["facts"][key] = value

    # -----------------------------
    # Store Conversation
    # -----------------------------

    def store_conversation(self, user, assistant):

        self.memory["conversation"].append({
            "user": user,
            "assistant": assistant
        })

    # -----------------------------
    # Retrieve Memory
    # -----------------------------

    def retrieve(self):

        return self.memory