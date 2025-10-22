import pickle, os
BASE_DIR = r"C:\Users\rahul\Desktop\Coding\Calculus_Carbon_Assignment"
DATA_DIR = os.path.join(BASE_DIR, "data")

with open(os.path.join(DATA_DIR, "meta.pkl"), "rb") as f:
    docs = pickle.load(f)

print("Total documents:", len(docs))
for i, d in enumerate(docs[:10]):  # print first 10 chunks
    print(f"\n[{i}] Source: {d['source']}")
    print(d['text'][:500])
