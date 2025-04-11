import anthropic

client = anthropic.Anthropic(api_key="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")

models = client.models.list()
for model in models:
    print(model.id)