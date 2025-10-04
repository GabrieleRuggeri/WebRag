# Requires transformers>=4.51.0
import torch
from typing import Optional


class Reranker:
    """Lightweight reranker wrapper around a causal LM reranker checkpoint.

    Features / optimizations added:
    - Lazy model/tokenizer loading (no heavy download on import)
    - Dependency injection for tokenizer/model for fast, offline unit tests
    - Minimal allocations and local var lookups reduced in hot paths
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-Reranker-0.6B",
        max_length: int = 8192,
        device: Optional[str] = None,
        tokenizer=None,
        model=None,
    ):
        # allow passing tokenizer/model for fast tests or custom backends
        self._provided_tokenizer = tokenizer
        self._provided_model = model
        self._model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.max_length = max_length

        # internal state filled on _ensure_model_loaded
        self.tokenizer = None
        self.model = None
        self.token_false_id = None
        self.token_true_id = None
        self.prefix_tokens = None
        self.suffix_tokens = None
        self._loaded = False

        # static prompt parts
        self._prefix = (
            "<|im_start|>system\n"
            "Judge whether the Document meets the requirements based on the Query and the Instruct provided. Note that the answer can only be \"yes\" or \"no\".<|im_end|>\n"
            "<|im_start|>user\n"
        )
        self._suffix = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"

    def _ensure_model_loaded(self):
        if self._loaded:
            return
        # use provided tokenizer/model if passed
        if self._provided_tokenizer is not None and self._provided_model is not None:
            self.tokenizer = self._provided_tokenizer
            self.model = self._provided_model
        else:
            # import here so tests can monkeypatch transformers before this runs
            from transformers import AutoTokenizer, AutoModelForCausalLM

            self.tokenizer = AutoTokenizer.from_pretrained(self._model_name, padding_side='left')
            self.model = AutoModelForCausalLM.from_pretrained(self._model_name).eval()
            self.model.to(self.device)

        # prepare token ids and prefix/suffix token lists
        self.token_false_id = self.tokenizer.convert_tokens_to_ids("no")
        self.token_true_id = self.tokenizer.convert_tokens_to_ids("yes")
        self.prefix_tokens = self.tokenizer.encode(self._prefix, add_special_tokens=False)
        self.suffix_tokens = self.tokenizer.encode(self._suffix, add_special_tokens=False)
        self._loaded = True

    def _format_instruction(self, instruction: Optional[str], query: str, doc: str) -> str:
        if instruction is None:
            instruction = 'Given a web search query, retrieve relevant passages that answer the query'
        # small, fast formatting
        return f"<Instruct>: {instruction}\n<Query>: {query}\n<Document>: {doc}"

    def _process_inputs(self, pairs: list[str]):
        tokenizer = self.tokenizer
        prefix_tokens = self.prefix_tokens
        suffix_tokens = self.suffix_tokens
        max_len = self.max_length - len(prefix_tokens) - len(suffix_tokens)

        inputs = tokenizer(
            pairs,
            padding=False,
            truncation='longest_first',
            return_attention_mask=False,
            max_length=max_len,
        )
        # preprend/append tokens per-example
        input_ids = inputs['input_ids']
        for i in range(len(input_ids)):
            input_ids[i] = prefix_tokens + input_ids[i] + suffix_tokens
        # pad and convert to tensors
        inputs = tokenizer.pad(inputs, padding=True, return_tensors="pt", max_length=self.max_length)
        # move tensors to device
        for k, v in list(inputs.items()):
            inputs[k] = v.to(self.device)
        return inputs

    @torch.no_grad()
    def _compute_logits(self, inputs):
        # get logits for last token and compute probability yes
        logits = self.model(**inputs).logits[:, -1, :]
        true_vector = logits[:, self.token_true_id]
        false_vector = logits[:, self.token_false_id]
        stacked = torch.stack([false_vector, true_vector], dim=1)
        probs = torch.nn.functional.log_softmax(stacked, dim=1)[:, 1].exp().tolist()
        return probs

    def rerank(self, query: str, documents: list[str], instruction: Optional[str] = None) -> list[float]:
        """Given a single query and a list of document strings, return a list of scores.

        Scores are floats in [0,1] where higher means more relevant.
        """
        if not documents:
            return []
        self._ensure_model_loaded()
        pairs = [self._format_instruction(instruction, query, d) for d in documents]
        inputs = self._process_inputs(pairs)
        return self._compute_logits(inputs)


if __name__ == "__main__":
    # small example
    reranker = Reranker()
    docs = ["The capital of China is Beijing.", "Gravity is a force..."]
    print(reranker.rerank("What is the capital of China?", docs))
