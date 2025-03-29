--- Example Usage ---
```
 
 vs_interface = VectorStoreInterface()
 COLLECTION = "my_test_docs"

 # Add data
 vs_interface.add(
     collection_name=COLLECTION,
     ids=["doc1", "doc2"],
     documents=["This is document one about apples.", "This is document two about oranges."],
     metadatas=[{"source": "manual"}, {"source": "manual"}]
 )

 # Query data
 query_results = vs_interface.query(
     collection_name=COLLECTION,
     query_texts=["Information about fruit"],
     n_results=1
 )

 if query_results and query_results[0]:
     print("Query Result:", query_results[0][0])

 # Get data
 item = vs_interface.get_items(COLLECTION, ids=["doc1"])
 if item:
#     print("Get Result:", item[0])

```