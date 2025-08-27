"""Model constants and definitions."""

from typing import Dict
from services.llm.types import ModelInfo

# Model ID constants
DEEPSEEK_V3_0324 = "openrouter/deepseek/deepseek-chat-v3-0324:free"
DEEPSEEK_V3_0324_PAID = "openrouter/deepseek/deepseek-chat-v3-0324"
DEEPSEEK_V3_0324_SHORT = "deepseek/deepseek-chat-v3-0324:free"
KIMI_K2 = "openrouter/moonshotai/kimi-k2:free"
DEEPSEEK_CHIMERA = "openrouter/tngtech/deepseek-r1t2-chimera:free"
DEEPSEEK_R1_0528 = "openrouter/deepseek/deepseek-r1-0528:free"
GEMINI_2_5_FLASH = "openrouter/google/gemini-2.5-flash"
QWEN_3_235B_A22B_2507 = "openrouter/qwen/qwen3-235b-a22b-2507"
MISTRAL_NEMO = "openrouter/mistralai/mistral-nemo"
DOLPHIN_MISTRAL_24B = (
    "openrouter/cognitivecomputations/dolphin-mistral-24b-venice-edition:free"
)
GEMINI_2_5_FLASH_IMAGE_PREVIEW = "openrouter/google/gemini-2.5-flash-image-preview:free"

GEMINI_2_5_FLASH_GG = "aistudio/gemini-2.5-flash"
GEMINI_2_5_FLASH_LITE_GG = "aistudio/gemini-2.5-flash-lite"
GEMINI_2_5_PRO_GG = "aistudio/gemini-2.5-pro"

# Model display name constants
DEEPSEEK_V3_NAME = "DeepSeek V3 0324"
DEEPSEEK_V3_PAID_NAME = "DeepSeek V3 0324 (paid)"
KIMI_K2_NAME = "Kimi K2"
DEEPSEEK_CHIMERA_NAME = "DeepSeek Chimera"
DEEPSEEK_R1_NAME = "DeepSeek R1 0528"
GEMINI_2_5_FLASH_NAME = "Gemini 2.5 Flash"
QWEN_3_235B_NAME = "Qwen 3 235B A22B Instruct 2507"
MISTRAL_NEMO_NAME = "Mistral Nemo"
DOLPHIN_MISTRAL_24B_NAME = "Venice Uncensored"
GEMINI_2_5_FLASH_IMAGE_PREVIEW_NAME = "Gemini 2.5 Flash Image Preview"

GEMINI_2_5_FLASH_GG_NAME = "Gemini 2.5 Flash (Aistudio)"
GEMINI_2_5_FLASH_LITE_GG_NAME = "Gemini 2.5 Flash Lite (Aistudio)"
GEMINI_2_5_PRO_GG_NAME = "Gemini 2.5 Pro (Aistudio)"

# Model display names
MODEL_NAMES = {
    DEEPSEEK_V3_NAME: DEEPSEEK_V3_0324,
    DEEPSEEK_V3_PAID_NAME: DEEPSEEK_V3_0324_PAID,
    KIMI_K2_NAME: KIMI_K2,
    DEEPSEEK_CHIMERA_NAME: DEEPSEEK_CHIMERA,
    DEEPSEEK_R1_NAME: DEEPSEEK_R1_0528,
    GEMINI_2_5_FLASH_NAME: GEMINI_2_5_FLASH,
    QWEN_3_235B_NAME: QWEN_3_235B_A22B_2507,
    MISTRAL_NEMO_NAME: MISTRAL_NEMO,
    GEMINI_2_5_FLASH_IMAGE_PREVIEW_NAME: GEMINI_2_5_FLASH_IMAGE_PREVIEW,
    GEMINI_2_5_FLASH_GG_NAME: GEMINI_2_5_FLASH_GG,
    GEMINI_2_5_FLASH_LITE_GG_NAME: GEMINI_2_5_FLASH_LITE_GG,
    GEMINI_2_5_PRO_GG_NAME: GEMINI_2_5_PRO_GG,
}

# Model information definitions
MODEL_INFOS: Dict[str, ModelInfo] = {
    DEEPSEEK_V3_NAME: ModelInfo(
        id=DEEPSEEK_V3_0324,
        name="DeepSeek V3 0324 (free)",
        provider="openrouter",
        context_length=163840,
        supports_tools=True,
        cost_per_million_tokens={"in": 0, "out": 0},
        description="DeepSeek V3, a 685B-parameter, mixture-of-experts model, is the latest iteration of the flagship chat model family from the DeepSeek team. It succeeds the DeepSeek V3 model and performs really well on a variety of tasks.",
    ),
    DEEPSEEK_V3_PAID_NAME: ModelInfo(
        id=DEEPSEEK_V3_0324_PAID,
        name="DeepSeek V3 0324 (paid)",
        provider="openrouter",
        context_length=163840,
        supports_tools=True,
        cost_per_million_tokens={"in": 0.18, "out": 0.72},
        description="DeepSeek V3, a 685B-parameter, mixture-of-experts model, is the latest iteration of the flagship chat model family from the DeepSeek team. It succeeds the DeepSeek V3 model and performs really well on a variety of tasks.",
    ),
    KIMI_K2_NAME: ModelInfo(
        id=KIMI_K2,
        name="Kimi K2 (free)",
        provider="openrouter",
        context_length=1000000,
        supports_tools=True,
        cost_per_million_tokens={"in": 0, "out": 0},
        description="Kimi K2 Instruct is a large-scale Mixture-of-Experts (MoE) language model developed by Moonshot AI, featuring 1 trillion total parameters with 32 billion active per forward pass. It is optimized for agentic capabilities, including advanced tool use, reasoning, and code synthesis. Kimi K2 excels across a broad range of benchmarks, particularly in coding (LiveCodeBench, SWE-bench), reasoning (ZebraLogic, GPQA), and tool-use (Tau2, AceBench) tasks. It supports long-context inference up to 128K tokens and is designed with a novel training stack that includes the MuonClip optimizer for stable large-scale MoE training.",
    ),
    DEEPSEEK_CHIMERA_NAME: ModelInfo(
        id=DEEPSEEK_CHIMERA,
        name="DeepSeek R1T2 Chimera (free)",
        provider="openrouter",
        context_length=163840,
        supports_tools=False,
        cost_per_million_tokens={"in": 0, "out": 0},
        description="DeepSeek-TNG-R1T2-Chimera is the second-generation Chimera model from TNG Tech. It is a 671 B-parameter mixture-of-experts text-generation model assembled from DeepSeek-AI's R1-0528, R1, and V3-0324 checkpoints with an Assembly-of-Experts merge. The tri-parent design yields strong reasoning performance while running roughly 20 % faster than the original R1 and more than 2× faster than R1-0528 under vLLM, giving a favorable cost-to-intelligence trade-off. The checkpoint supports contexts up to 60 k tokens in standard use (tested to ~130 k) and maintains consistent <think> token behaviour, making it suitable for long-context analysis, dialogue and other open-ended generation tasks.",
    ),
    DEEPSEEK_R1_NAME: ModelInfo(
        id=DEEPSEEK_R1_0528,
        name="DeepSeek R1 0528 (free)",
        provider="openrouter",
        context_length=163840,
        supports_tools=False,
        cost_per_million_tokens={"in": 0, "out": 0},
        description="May 28th update to the original DeepSeek R1 Performance on par with OpenAI o1, but open-sourced and with fully open reasoning tokens. It's 671B parameters in size, with 37B active in an inference pass. Fully open-source model.",
    ),
    GEMINI_2_5_FLASH_NAME: ModelInfo(
        id=GEMINI_2_5_FLASH,
        name="Gemini 2.5 Flash",
        provider="openrouter",
        context_length=1048576,
        supports_tools=True,
        cost_per_million_tokens={"in": 0.30, "out": 2.50},
        description='Gemini 2.5 Flash is Google\'s state-of-the-art workhorse model, specifically designed for advanced reasoning, coding, mathematics, and scientific tasks. It includes built-in "thinking" capabilities, enabling it to provide responses with greater accuracy and nuanced context handling. Additionally, Gemini 2.5 Flash is configurable through the "max tokens for reasoning" parameter, as described in the documentation.',
    ),
    QWEN_3_235B_NAME: ModelInfo(
        id=QWEN_3_235B_A22B_2507,
        name="Qwen 3 235B A22B Instruct 2507",
        provider="openrouter",
        context_length=32768,
        supports_tools=True,
        cost_per_million_tokens={"in": 0.078, "out": 0.312},
        description='Qwen3-235B-A22B-Instruct-2507 is a multilingual, instruction-tuned mixture-of-experts language model based on the Qwen3-235B architecture, with 22B active parameters per forward pass. It is optimized for general-purpose text generation, including instruction following, logical reasoning, math, code, and tool usage. The model supports a native 262K context length and does not implement "thinking mode" (<think> blocks). Compared to its base variant, this version delivers significant gains in knowledge coverage, long-context reasoning, coding benchmarks, and alignment with open-ended tasks. It is particularly strong on multilingual understanding, math reasoning (e.g., AIME, HMMT), and alignment evaluations like Arena-Hard and WritingBench.',
    ),
    MISTRAL_NEMO_NAME: ModelInfo(
        id=MISTRAL_NEMO,
        name="Mistral Nemo",
        provider="openrouter",
        context_length=32000,
        supports_tools=True,
        cost_per_million_tokens={"in": 0.008, "out": 0.05},
        description="A 12B parameter model with a 128k token context length built by Mistral in collaboration with NVIDIA. The model is multilingual, supporting English, French, German, Spanish, Italian, Portuguese, Chinese, Japanese, Korean, Arabic, and Hindi. It supports function calling and is released under the Apache 2.0 license.",
    ),
    DOLPHIN_MISTRAL_24B_NAME: ModelInfo(
        id=DOLPHIN_MISTRAL_24B,
        name="Venice Uncensored",
        provider="openrouter",
        context_length=32768,
        supports_tools=False,
        cost_per_million_tokens={"in": 0.0, "out": 0.0},
        description="Venice Uncensored Dolphin Mistral 24B Venice Edition is a fine-tuned variant of Mistral-Small-24B-Instruct-2501, developed by dphn.ai in collaboration with Venice.ai. This model is designed as an “uncensored” instruct-tuned LLM, preserving user control over alignment, system prompts, and behavior. Intended for advanced and unrestricted use cases, Venice Uncensored emphasizes steerability and transparent behavior, removing default safety and alignment layers typically found in mainstream assistant models.",
    ),
    GEMINI_2_5_FLASH_IMAGE_PREVIEW_NAME: ModelInfo(
        id=GEMINI_2_5_FLASH_IMAGE_PREVIEW,
        name="Gemini 2.5 Flash Image Preview",
        provider="openrouter",
        context_length=1048576,
        supports_tools=False,
        text=False,
        image_gen=True,
        cost_per_million_tokens={"in": 0.00, "out": 0.00},
        description="Gemini 2.5 Flash Image Preview is a state of the art image generation model with contextual understanding. It is capable of image generation, edits, and multi-turn conversations.",
    ),
    # NOTE: Aistudio models, tools are all disabled, for now
    GEMINI_2_5_FLASH_GG_NAME: ModelInfo(
        id=GEMINI_2_5_FLASH_GG,
        name="Gemini 2.5 Flash (Aistudio)",
        provider="aistudio",
        context_length=1048576,
        supports_tools=False,
        cost_per_million_tokens={"in": 0.00, "out": 0.00},
        description="Google's best model in terms of price-performance, offering well-rounded capabilities. 2.5 Flash is best for large scale processing, low-latency, high volume tasks that require thinking, and agentic use cases.",
    ),
    GEMINI_2_5_FLASH_LITE_GG_NAME: ModelInfo(
        id=GEMINI_2_5_FLASH_LITE_GG,
        name="Gemini 2.5 Flash Lite (Aistudio)",
        provider="aistudio",
        context_length=1048576,
        supports_tools=False,
        cost_per_million_tokens={"in": 0.00, "out": 0.00},
        description="A Gemini 2.5 Flash model optimized for cost-efficiency and high throughput.",
    ),
    GEMINI_2_5_PRO_GG_NAME: ModelInfo(
        id=GEMINI_2_5_PRO_GG,
        name="Gemini 2.5 Pro (Aistudio)",
        provider="aistudio",
        context_length=1048576,
        supports_tools=False,
        cost_per_million_tokens={"in": 0.00, "out": 0.00},
        description="Gemini 2.5 Pro is Google's state-of-the-art thinking model, capable of reasoning over complex problems in code, math, and STEM, as well as analyzing large datasets, codebases, and documents using long context.",
    ),
}
