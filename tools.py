SYSTEM_PROMPT = (
    "You are a professional bank customer service agent handling phone calls. "
    "When a customer wants to access account information, you MUST verify their "
    "identity first. Verification requires ALL THREE of the following:\n"
    "  1. Full name\n"
    "  2. Date of birth\n"
    "  3. Last 4 digits of their Social Security Number\n\n"
    "If the customer is reluctant, hesitant, or refuses to provide any of this "
    "information, politely explain why it is necessary (security, fraud prevention, "
    "regulatory compliance) and reassure them that their data is protected. "
    "Do NOT proceed without all three pieces of information. Do NOT make up or "
    "assume any verification details.\n\n"
    "Once you have all three, call verify_identity. Only after successful "
    "verification, call get_account_balance to retrieve their balance.\n\n"
    "Be patient, empathetic, professional, and concise."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "verify_identity",
            "description": (
                "Verify a bank customer's identity by checking their name, "
                "date of birth, and last 4 digits of SSN against the bank's "
                "database. Must be called before any account operations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The customer's full name",
                    },
                    "date_of_birth": {
                        "type": "string",
                        "description": "Date of birth in YYYY-MM-DD format",
                    },
                    "ssn_last_4": {
                        "type": "string",
                        "description": "Last 4 digits of the SSN",
                    },
                },
                "required": ["name", "date_of_birth", "ssn_last_4"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_account_balance",
            "description": (
                "Retrieve account balance(s) for a verified customer. "
                "Requires the user_id returned from a successful verify_identity call."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "Internal user ID from verify_identity",
                    },
                },
                "required": ["user_id"],
            },
        },
    },
]
