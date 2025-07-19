from gitingest import ingest

summary, tree, content = ingest(".")

print("--- Summary ---")
print(summary)
print("\n--- Tree ---")
print(tree)
print("\n--- Content ---")
# The content is likely to be very large, so I will just print a confirmation message.
print("Content was ingested successfully.")
