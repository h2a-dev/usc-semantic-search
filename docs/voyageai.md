Introduction
Suggest Edits
Voyage AI provides cutting-edge embedding and rerankers.

Embedding models are neural net models (e.g., transformers) that convert unstructured and complex data, such as documents, images, audios, videos, or tabular data, into dense numerical vectors (i.e. embeddings) that capture their semantic meanings. These vectors serve as representations/indices for datapoints and are essential building blocks for semantic search and retrieval-augmented generation (RAG), which is the predominant approach for domain-specific or company-specific chatbots and other AI applications.

Rerankers are neural nets that output relevance scores between a query and multiple documents. It is common practice to use the relevance scores to rerank the documents initially retrieved with embedding-based methods (or with lexical search algorithms such as BM25 and TF-IDF). Selecting the highest-scored documents refines the retrieval results into a more relevant subset.

Voyage AI provides API endpoints for embedding and reranking models that take in your data (e.g., documents, queries, or query-document pairs) and return their embeddings or relevance scores. Embedding models and rerankers, as modular components, seamlessly integrate with other parts of a RAG stack, including vector stores and generative Large Language Models (LLMs).

Voyage AI’s embedding models and rerankers are state-of-the-art in retrieval accuracy. Please read our announcing blog post for details. Please also check out a high-level introduction of embedding models, semantic search, and RAG, and our step-by-step quickstart tutorial on implementing a minimalist RAG chatbot using Voyage model endpoints.

API Key and Python Client
Suggest Edits
Authentication with API Keys
Voyage AI utilizes API keys to monitor usage and manage permissions. To obtain your key, please sign in with your Voyage AI account and click the "Create new secret key" button in the API keys section of the Voyage dashboard. We recommend setting the API key as an environment variable. For example, in MacOS or Linux, type the following command in the terminal, replacing <your secret key> with your actual API key:

Shell

export VOYAGE_API_KEY="<your secret key>"
You can verify the setup by typing echo $VOYAGE_API_KEY in the terminal. It should display your API key.

Your API key is supposed to be secret -- please avoid sharing it or exposing it in browsers or apps. Please store your API key securely for future use.

Install Voyage Python Package
You can interact with the API through HTTP requests from any language. For Python users, we offer an official package which can be installed via pip :

Shell

pip install -U voyageai
We recommend using the -U or --upgrade option to ensure you are installing the latest version of the package. This helps you access the most recent features and bug fixes.

After installation, you can test it by running:

Shell

python -c "import voyageai"
The installation is successful if this command runs without any errors.

voyageai.Client
The Python package offers the voyageai.Client class as the interface to invoke Voyage's API. You can create a client object and use it to access the predictions by our models.

class voyageai.Client

Parameters

api_key (str, optional, defaults to None) - Voyage API key. If None, the client will search for the API key in the following order:
voyageai.api_key_path, path to the file containing the key;
environment variable VOYAGE_API_KEY_PATH, which can be set to the path to the file containing the key;
voyageai.api_key, an attribute of the voyageai module, which can be used to store the key;
environment variable VOYAGE_API_KEY.
max_retries (int, defaults to 0) - Maximum number of retries for each API request in case of rate limit errors or temporary server unavailability. The client employs a wait-and-retry strategy to handle such errors, and will raise an exception upon reaching the maximum retry limit. By default, the client does not retry.
timeout (int, optional, defaults to None) - Maximum time in seconds to wait for a response from the API before aborting the request. If the specified timeout is exceeded, the request is terminated and a timeout exception is raised. By default, no timeout constraint is enforced.
Example

Python

import voyageai

vo = voyageai.Client()
# This will automatically use the environment variable VOYAGE_API_KEY.
# Alternatively, you can use vo = voyageai.Client(api_key="<your secret key>")

result = vo.embed(["hello world"], model="voyage-3.5")
voyageai.AsyncClient
The Python package provides a voyageai.AsyncClient class designed for asynchronous API calls. This AsyncClient class mirrors the Client class in terms of method offerings and input/output specifications but is tailored for asynchronous operations, enabling non-blocking API requests.

Example

Python

import voyageai

vo = voyageai.AsyncClient()
# This will automatically use the environment variable VOYAGE_API_KEY.
# Alternatively, you can use vo = voyageai.AsyncClient(api_key="<your secret key>")

result = await vo.embed(["hello world"], model="voyage-3.5")

Quickstart Tutorial
Suggest Edits
This tutorial is a step-by-step guidance on implementing a specialized chatbot with RAG stack using embedding models (e.g., Voyage embeddings) and large language models (LLMs). We start with a brief overview of the retrieval augmented generation (RAG) stack. Then, we’ll briefly go through the preparation and vectorization of data (i.e. embeddings). We’ll show how to do retrieval with embeddings as well as some additional refinements with rerankers. Finally, we’ll put this all together to create a simple RAG chatbot.

Brief overview of the RAG stack
A typical RAG stack is illustrated in Figure 1. When presented with a search query, our initial step involves employing the embedding model, such as Voyage embeddings, to derive the vector representation of the query. Subsequently, we conduct a document search, identifying the most relevant documents from a vector store The most relevant document is then selected and combined with the original query. This composite input is then submitted to a generative model to generate a comprehensive response to the query. This RAG stack can be further refined with reranking, which we’ll discuss in a later section.

Figure 1: Typical RAG stack
Figure 1: Typical RAG stack

Prepare data
You will need a corpus of documents that your chatbot will specialize in. You can choose to save your documents as demonstrated below or use the following set of documents as a starting point.

Python

documents = [
    "The Mediterranean diet emphasizes fish, olive oil, and vegetables, believed to reduce chronic diseases.",
    "Photosynthesis in plants converts light energy into glucose and produces essential oxygen.",
    "20th-century innovations, from radios to smartphones, centered on electronic advancements.",
    "Rivers provide water, irrigation, and habitat for aquatic species, vital for ecosystems.",
    "Apple’s conference call to discuss fourth fiscal quarter results and business updates is scheduled for Thursday, November 2, 2023 at 2:00 p.m. PT / 5:00 p.m. ET.",
    "Shakespeare's works, like 'Hamlet' and 'A Midsummer Night's Dream,' endure in literature."
]
We have additional examples available in this link for you to download and test.

Vectorize/embed the documents
First, follow the installation guide to install the Voyage Python package and get your API key. Then, we can use the Python client to create embeddings.

Embed a small number of documents
Embed a large number of documents

import voyageai

vo = voyageai.Client()
# This will automatically use the environment variable VOYAGE_API_KEY.
# Alternatively, you can use vo = voyageai.Client(api_key="<your secret key>")

# Embed the documents
documents_embeddings = vo.embed(
    documents, model="voyage-3.5", input_type="document"
).embeddings
Notes on Tokenization
A minimalist retrieval system
The main feature of the embeddings is that the cosine similarity between two embeddings captures the semantic relatedness of the corresponding original passages. This allows us to use the embeddings to do semantic retrieval / search.

Suppose the user sends a "query" (e.g., a question or a comment) to the chatbot:

Python

query = "When is Apple's conference call scheduled?"
To find out the document that is most similar to the query among the existing data, we can first embed/vectorize the query:

Python

# Get the embedding of the query
query_embedding = vo.embed([query], model="voyage-3.5", input_type="query").embeddings[0]
Nearest neighbor Search: We can find the closest embedding among the documents based on the cosine similarity, and retrieve the corresponding document.

Python

# Compute the similarity
# Voyage embeddings are normalized to length 1, therefore dot-product and cosine 
# similarity are the same.
similarities = np.dot(doc_embds, query_embd)

retrieved_id = np.argmax(similarities)
print(documents[retrieved_id])
k-nearest neighbors Search (k-NN): It is often useful to retrieve not only the closest document but also the k most closest documents. We can use any k_nearest_neighbors search algorithm to achieve this goal.

Python

# Use the k-nearest neighbor algorithm to identify the top-k documents with the highest similarity
retrieved_embds, retrieved_embd_indices = k_nearest_neighbors(
    query_embedding, documents_embeddings, k=3
)
retrieved_docs = [documents[index] for index in retrieved_embd_indices]
Notes on Cosine Similarity, Nearest Neighbor Search, and Vector Database
Refinement with rerankers
We can further refine our embedding-based retrieval with rerankers. The refined RAG stack with a reranker is illustrated in Figure 2. Here, the retrieved documents from the vector store are subsequently passed to a reranker, which then reranks the documents for semantic relevance against the query and produces a more relevant and smaller set of documents for inputting to the generative model.

Figure 2: RAG stack with reranker 
Figure 2: RAG stack with reranker

Below, we send initially retrieved documents to the reranker to obtain the top-3 most relevant documents.

Python

# Reranking
documents_reranked = vo.rerank(query, documents, model="rerank-2", top_k=3)
We see that the reranker properly ranks the Apple conference call document as the most relevant to the query.

Python

for r in documents_reranked.results:
    print(f"Document: {r.document}")
    print(f"Relevance Score: {r.relevance_score}")
    print(f"Index: {r.index}")
    print()
Output:

Text

Document: Apple’s conference call to discuss fourth fiscal quarter results and business updates is scheduled for Thursday, November 2, 2023 at 2:00 p.m. PT / 5:00 p.m. ET.
Relevance Score: 0.9296875
Index: 4


Document: The Mediterranean diet emphasizes fish, olive oil, and vegetables, believed to reduce chronic diseases.
Relevance Score: 0.40625
Index: 0


Document: Photosynthesis in plants converts light energy into glucose and produces essential oxygen.
Relevance Score: 0.39453125
Index: 1
A minimalist RAG chatbot
The Retrieval-Augmented Generation (RAG) chatbot represents a cutting-edge approach in conversational artificial intelligence. RAG combines the powers of retrieval-based and generative methods to produce more accurate and contextually relevant responses. RAG can leverage a large corpora of text to retrieve relevant documents and then send those documents to language models, such as Claude or GPT, to generate replies. This methodology ensures that the chatbot's answers are both informed by vast amounts of information and tailored to the specifics of the user's query.

Suppose you have implemented a semantic search system as described in the previous section---either with or without a reranker. As a result of the search process, you have retrieved the most relevant document, referred to as retrieved_doc. We can craft a prompt with this context which we can use as input to the language model.

Python

# Take the retrieved document and use it as a prompt for the text generation model
prompt = f"Based on the information: '{retrieved_doc}', generate a response of {query}"
Now you can utilize a text generation model like Claude 3.5 Sonnet to craft a response based on the provided query and the retrieved document.

Install the anthropic package first:

Shell

pip install anthropic
Then run the following code:

Python

import anthropic

# Initialize Anthropic API
client = anthropic.Anthropic(api_key="YOUR ANTHROPIC API KEY")

message = client.messages.create(
    model="claude-3-5-sonnet-20240620",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": prompt}
    ]
)

print(message.content[0].text)
Output:


Apple's conference call is scheduled for Thursday, November 2, 2023 at 2:00 p.m. PT / 5:00 p.m. ET.
Output without using Voyage retrieved documents


I don't have information about a specific upcoming Apple conference call. Apple typically holds quarterly earnings conference calls, but without a more precise timeframe or context, I can't provide the exact date of their next scheduled call. For the most up-to-date information on Apple's upcoming conference calls or earnings releases, you should check Apple's investor relations website or contact their investor relations department directly.
You can do the same with GPT-4o as well. Install the openai package first:

Shell

pip install openai
Then run the following code:

Python

from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key="YOUR OPENAI API KEY")

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt},
    ],
)

print(response.choices[0].message.content)
Output:

Text

Apple's conference call is scheduled for Thursday, November 2, 2023 at 2:00 p.m. PT / 5:00 p.m. ET.
Output without using Voyage retrieved documents:

Text

Apple's conference calls are typically scheduled to discuss quarterly earnings. They usually announce these dates a few weeks in advance. For the specific date and time of the next Apple conference call, I recommend checking Apple's Investor Relations website or recent press releases, as they will have the most accurate and up-to-date information. If you're looking for the scheduled call for a specific quarter, these events usually occur a few weeks after the end of a fiscal quarter, with Apple's fiscal year ending on the last Saturday of September.
Colab examples
To execute the code examples provided above in Google Colab, please review and run the code snippets in Google Colaboratory.

Text Embeddings
Suggest Edits
Model Choices
Voyage currently provides the following text embedding models:

Model
Context Length (tokens)	
Embedding Dimension
Description
voyage-3-large	32,000	1024 (default), 256, 512, 2048	The best general-purpose and multilingual retrieval quality. See blog post for details.
voyage-3.5	32,000	1024 (default), 256, 512, 2048	Optimized for general-purpose and multilingual retrieval quality. See blog post for details.
voyage-3.5-lite	32,000	1024 (default), 256, 512, 2048	Optimized for latency and cost. See blog post for details.
voyage-code-3	32,000	1024 (default), 256, 512, 2048	Optimized for code retrieval. See blog post for details.
voyage-finance-2	32,000	1024	Optimized for finance retrieval and RAG. See blog post for details.
voyage-law-2	16,000	1024	Optimized for legal retrieval and RAG. Also improved performance across all domains. See blog post for details.
voyage-code-2	16,000	1536	Optimized for code retrieval (17% better than alternatives) / Previous generation of code embeddings. See blog post for details.
Need help deciding which text embedding model to use? Check out our FAQ.

Older models
Python API
Voyage text embeddings are accessible in Python through the voyageai package. Please install the voyageai package, set up the API key, and use the voyageai.Client.embed() function to vectorize your inputs.

voyageai.Client.embed (texts : List[str], model : str, input_type : Optional[str] = None, truncation : Optional[bool] = None, output_dimension: Optional[int] = None, output_dtype: Optional[str] = "float")

Parameters

texts (str or List[str]) - A single text string, or a list of texts as a list of strings, such as ["I like cats", "I also like dogs"]. Currently, we have two constraints on the list:
The maximum length of the list is 1,000.
The total number of tokens in the list is at most 1M for voyage-3.5-lite; 320K for voyage-3.5 and voyage-2; and 120K for voyage-3-large, voyage-code-3, voyage-large-2-instruct, voyage-finance-2, voyage-multilingual-2, and voyage-law-2.
model (str) - Name of the model. Recommended options: voyage-3-large, voyage-3.5, voyage-3.5-lite, voyage-code-3, voyage-finance-2, voyage-law-2.
input_type (str, optional, defaults to None) - Type of the input text. Options: None, query, document.
When input_type is None , the embedding model directly converts the inputs (texts) into numerical vectors. For retrieval/search purposes, where a "query" is used to search for relevant information among a collection of data, referred to as "documents", we recommend specifying whether your inputs (texts) are intended as queries or documents by setting input_type to query or document , respectively. In these cases, Voyage automatically prepends a prompt to your inputs (texts) before vectorizing them, creating vectors more tailored for retrieval/search tasks. Embeddings generated with and without the input_type argument are compatible.
For transparency, the following prompts are prepended to your input.
For query, the prompt is "Represent the query for retrieving supporting documents: ".
For document, the prompt is "Represent the document for retrieval: ".
truncation (bool, optional, defaults to True) - Whether to truncate the input texts to fit within the context length.
If True, an over-length input texts will be truncated to fit within the context length, before vectorized by the embedding model.
If False, an error will be raised if any given text exceeds the context length.
output_dimension (int, optional, defaults to None) - The number of dimensions for resulting output embeddings.
Most models only support a single default dimension, used when output_dimension is set to None (see model embedding dimensions above).
voyage-3-large, voyage-3.5, voyage-3.5-lite, and voyage-code-3 support the following output_dimension values: 2048, 1024 (default), 512, and 256.
output_dtype (str, optional, defaults to float) - The data type for the embeddings to be returned. Options: float, int8, uint8, binary, ubinary. float is supported for all models. int8, uint8, binary, and ubinary are supported by voyage-3-large, voyage-3.5, voyage-3.5-lite, and voyage-code-3. Please see our guide for more details about output data types.
float: Each returned embedding is a list of 32-bit (4-byte) single-precision floating-point numbers. This is the default and provides the highest precision / retrieval accuracy.
int8 and uint8: Each returned embedding is a list of 8-bit (1-byte) integers ranging from -128 to 127 and 0 to 255, respectively.
binary and ubinary: Each returned embedding is a list of 8-bit integers that represent bit-packed, quantized single-bit embedding values: int8 for binary and uint8 for ubinary. The length of the returned list of integers is 1/8 of output_dimension (which is the actual dimension of the embedding). The binary type uses the offset binary method. Please refer to our guide for details on offset binary and binary embeddings.
Returns

A EmbeddingsObject, containing the following attributes:
embeddings (List[List[float]] or List[List[int]]) - A list of embeddings for the corresponding list of input texts. Each embedding is a vector represented as a list of floats when output_dtype is set to float and as a list of integers for all other values of output_dtype (int8, uint8, binary, ubinary).
total_tokens (int) - The total number of tokens in the input texts.
Example

Python
Output

import voyageai

vo = voyageai.Client()
# This will automatically use the environment variable VOYAGE_API_KEY.
# Alternatively, you can use vo = voyageai.Client(api_key="<your secret key>")

texts = [
    "The Mediterranean diet emphasizes fish, olive oil, and vegetables, believed to reduce chronic diseases.",
    "Photosynthesis in plants converts light energy into glucose and produces essential oxygen.",
    "20th-century innovations, from radios to smartphones, centered on electronic advancements.",
    "Rivers provide water, irrigation, and habitat for aquatic species, vital for ecosystems.",
    "Apple’s conference call to discuss fourth fiscal quarter results and business updates is scheduled for Thursday, November 2, 2023 at 2:00 p.m. PT / 5:00 p.m. ET.",
    "Shakespeare's works, like 'Hamlet' and 'A Midsummer Night's Dream,' endure in literature."
]

# Embed the documents
result = vo.embed(texts, model="voyage-3.5", input_type="document")
print(result.embeddings)
Deprecated Functions
REST API
Voyage text embeddings can be accessed by calling the endpoint POST https://api.voyageai.com/v1/embeddings. Please refer to the Text Embeddings API Reference for the specification.

Example

Embed a single string
Embed a list of strings

curl https://api.voyageai.com/v1/embeddings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $VOYAGE_API_KEY" \
  -d '{
    "input": "Sample text",
    "model": "voyage-3.5",
    "input_type": "document"
  }'
TypeScript Library
Voyage text embeddings are accessible in TypeScript through the Voyage TypeScript Library, which exposes all the functionality of our text embeddings endpoint (see Text Embeddings API Reference).

Rerankers
Suggest Edits
A reranker, given a query and many documents, returns the (ranks of) relevancy between the query and documents. The documents oftentimes are the preliminary results from an embedding-based retrieval system, and the reranker refines the ranks of these candidate documents and provides more accurate relevancy scores.

Unlike embedding models that encode queries and documents separately, rerankers are cross-encoders that jointly process a pair of query and document, enabling more accurate relevancy prediction. Thus, it is a common practice to apply a reranker on the top candidates retrieved with embedding-based search (or with lexical search algorithms such as BM25 and TF-IDF).

Model Choice
Voyage currently provides the following reranker models:

Model
Context Length (tokens)	Description
rerank-2	16,000	Our generalist reranker optimized for quality with multilingual support. See blog post for details.
rerank-2-lite	8000	Our generalist reranker optimized for both latency and quality with multilingual support. See blog post for details.
Older models
Python API
Voyage reranker is accessible in Python through the voyageai package. Please first install the voyageai package and setup the API key.

Voyage reranker receives as input a query and a list of candidate documents, e.g., the documents retrieved by a nearest neighbor search with embeddings. It reranks the candidate documents according to their semantic relevances to the search query, and returns the list of relevance scores. To access the reranker, create a voyageai.Client object and use its rerank() method.

voyageai.Client.rerank (query: str, documents: List[str], model: str, top_k: Optional[int] = None, truncation: bool = True)

Parameters

query (str) - The query as a string. The query can contain a maximum of 4,000 tokens for rerank-2, 2,000 tokens for rerank-2-lite and rerank-1, and 1,000 tokens for rerank-lite-1.
documents (List[str]) - The documents to be reranked as a list of strings.
The number of documents cannot exceed 1,000.
The sum of the number of tokens in the query and the number of tokens in any single document cannot exceed 16,000 for rerank-2; 8,000 for rerank-2-lite and rerank-1; and 4,000 for rerank-lite-1.
The total number of tokens, defined as "the number of query tokens × the number of documents + sum of the number of tokens in all documents", cannot exceed 600K for rerank-2 and rerank-2-lite, and 300K for rerank-1 and rerank-lite-1. Please see our FAQ.
model (str) - Name of the model. Recommended options: rerank-2, rerank-2-lite.
top_k (int, optional, defaults to None) - The number of most relevant documents to return. If not specified, the reranking results of all documents will be returned.
truncation (bool, optional, defaults to True) - Whether to truncate the input to satisfy the "context length limit" on the query and the documents.
If True, the query and documents will be truncated to fit within the context length limit, before processed by the reranker model.
If False, an error will be raised when the query exceeds 4,000 tokens for rerank-2; 2,000 tokens rerank-2-lite and rerank-1; and 1,000 tokens for rerank-lite-1, or the sum of the number of tokens in the query and the number of tokens in any single document exceeds 16,000 for rerank-2; 8,000 for rerank-2-lite and rerank-1; and 4,000 for rerank-lite-1.
Returns

A RerankingObject, containing the following attributes:
results (List[RerankingResult]) - A list of RerankingResult, with format specified below, sorted by the descending order of relevance scores. The length of the list equals to top_k if this argument is specified, otherwise the number of the input documents. Each element in the list is a RerankingResult object, which contains attributes:
index (int) - The index of the document in the input list.
document (str) - The document as a string.
relevance_score (float) - The relevance score of the document with respect to the query.
total_tokens (int) - The total number of tokens in the input, which is defined as "the number of query tokens × the number of documents + sum of the number of tokens in all documents".
Example

Python
Output

import voyageai

vo = voyageai.Client()
# This will automatically use the environment variable VOYAGE_API_KEY.
# Alternatively, you can use vo = voyageai.Client(api_key="<your secret key>")

query = "When is Apple's conference call scheduled?"
documents = [
    "The Mediterranean diet emphasizes fish, olive oil, and vegetables, believed to reduce chronic diseases.",
    "Photosynthesis in plants converts light energy into glucose and produces essential oxygen.",
    "20th-century innovations, from radios to smartphones, centered on electronic advancements.",
    "Rivers provide water, irrigation, and habitat for aquatic species, vital for ecosystems.",
    "Apple’s conference call to discuss fourth fiscal quarter results and business updates is scheduled for Thursday, November 2, 2023 at 2:00 p.m. PT / 5:00 p.m. ET.",
    "Shakespeare's works, like 'Hamlet' and 'A Midsummer Night's Dream,' endure in literature."
]

reranking = vo.rerank(query, documents, model="rerank-2", top_k=3)
for r in reranking.results:
    print(f"Document: {r.document}")
    print(f"Relevance Score: {r.relevance_score}")
    print()
REST API
Voyage reranker can be accessed by calling the endpoint POST https://api.voyageai.com/v1/rerank. Please refer to the Reranker API Reference for the specification.

Example

Shell

curl https://api.voyageai.com/v1/rerank \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $VOYAGE_API_KEY" \
  -d '{
    "query": "Sample query",
    "documents": [
        "Sample document 1",
        "Sample document 2"
    ],
    "model": "rerank-2"
  }'
TypeScript Library
Voyage rerankers are accessible in TypeScript through the Voyage TypeScript Library, which exposes all the functionality of our reranker endpoint (see Reranker API Reference).
