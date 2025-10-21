Analyze this project and generate a plan of refactoring the architecture which must satisfy the following requirements

- this plan must includs ollama and vLLM two model providers

- the architecture include the for the following Layers

    * LLM Provider Layer:
    	- Including Ollama, vLLM, llama.cpp
    	- unified interfaces for Service Layer

    * Services Layer
    	- InputManager
    	- PromptManager
    	- RetrievalManager
