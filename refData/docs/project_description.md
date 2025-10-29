Role: you are a procifient and talent RAG application developer.
Project Description:
1. This is a "chat with your documentation" RAG application.
2. Users can upload their pdf, markdown, excel, csv files...etc.
3. The uploaded files will be extracted, processed and chunked then save to vector database, the whole flow like the following:
  [使用者] -> [Presentation Layer (Client)] -> FastAPI Endpoint (/upload) -> [Services Layer (InputDataHandleService)] -> [Services Layer (RetrievalService)] -> [Vector DB]
4.users can chat questions with their files, and all the responses **must come from** their files, no any other sources.
5. The system should keep the messages of chats.