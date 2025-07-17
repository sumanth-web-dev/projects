# playwrite_mcp.py
# This file provides a function to run Playwright actions for MCP integration.


# Simple in-memory chat history (for demo; use persistent storage for production)
chat_history = []

def run_playwright_action(action, params):
    """
    Run a Playwright action based on the action name and parameters.
    Supports 'example' and 'chat' actions.
    """
    if action == 'example':
        return {'message': 'Example action executed', 'params': params}
    elif action == 'chat':
        # params: {"user": str, "message": str}
        user = params.get('user', 'User')
        message = params.get('message', '')
        if not message:
            raise ValueError('Message cannot be empty.')
        chat_entry = {"user": user, "message": message}
        chat_history.append(chat_entry)
        # Limit history to last 20 messages
        if len(chat_history) > 20:
            chat_history.pop(0)
        return {"history": chat_history}
    else:
        raise ValueError(f'Unknown action: {action}')
