import json
from IPython.display import display, HTML
import markdown

class Tools:
    def __init__(self):
        self.tools = []
        self.functions = {}

    def add_tool(self, function, description):
        # Store the function for later execution
        self.functions[function.__name__] = function
        
        # Create the proper OpenAI function format
        tool_definition = {
            "type": "function",
            "function": description
        }
        self.tools.append(tool_definition)
    
    def get_tools(self):
        return self.tools

    def function_call(self, tool_call_response):
        function_name = tool_call_response.function.name
        arguments = json.loads(tool_call_response.function.arguments)

        f = self.functions[function_name]
        result = f(**arguments)

        return {
            "tool_call_id": tool_call_response.id,
            "role": "tool",
            "name": function_name,
            "content": json.dumps(result, indent=2),
        }


def shorten(text, max_length=50):
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


class ChatInterface:
    def input(self):
        question = input("You: ")
        return question
    
    def display(self, message):
        print(f"Assistant: {message}")

    def display_function_call(self, tool_call, result):
        call_html = f"""
            <details>
            <summary>Function call: <tt>{tool_call.function.name}({shorten(tool_call.function.arguments)})</tt></summary>
            <div>
                <b>Call</b>
                <pre>{tool_call.function.name}({tool_call.function.arguments})</pre>
            </div>
            <div>
                <b>Output</b>
                <pre>{result['content']}</pre>
            </div>
            </details>
        """
        display(HTML(call_html))

    def display_response(self, content):
        response_html = markdown.markdown(content)
        html = f"""
            <div>
                <div><b>Assistant:</b></div>
                <div>{response_html}</div>
            </div>
        """
        display(HTML(html))


class ChatAssistant:
    def __init__(self, tools, developer_prompt, chat_interface, client):
        self.tools = tools
        self.developer_prompt = developer_prompt
        self.chat_interface = chat_interface
        self.client = client
    
    def gpt(self, chat_messages):
        return self.client.chat.completions.create(
            model='gpt-4o',  # This should match your Azure deployment name
            messages=chat_messages,
            tools=self.tools.get_tools(),
            tool_choice="auto"
        )

    def run(self):
        chat_messages = [
            {"role": "system", "content": self.developer_prompt},
        ]

        # Chat loop
        while True:
            question = self.chat_interface.input()
            if question.strip().lower() == 'stop':  
                self.chat_interface.display("Chat ended.")
                break

            message = {"role": "user", "content": question}
            chat_messages.append(message)

            while True:  # inner request loop
                response = self.gpt(chat_messages)
                
                response_message = response.choices[0].message
                chat_messages.append(response_message)

                # Check if there are tool calls
                if response_message.tool_calls:
                    for tool_call in response_message.tool_calls:
                        result = self.tools.function_call(tool_call)
                        chat_messages.append(result)
                        self.chat_interface.display_function_call(tool_call, result)
                    # Continue the loop to get the final response
                    continue
                else:
                    # Display the assistant's response
                    if response_message.content:
                        self.chat_interface.display_response(response_message.content)
                    break