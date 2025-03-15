# SWESynInfer+: SoftWare Engineering Process Data Synthesis and Inference Workflow

## Overview

**SWE-Reasoner**:  is an open-source large language model specifically designed for software improvement. Built upon the foundation of the Qwen series base models, SWE-Reasoner has undergone additional LongCoT training using software engineering development process data to enhance its capabilities in solving complex software engineering tasks.

**SWESynInfer+**: four-stage software engineering process data synthesis and inference workflow. SWE-SynInfer divides the issue resolution process into three steps: (1) repository understanding to identify relevant codebase files, (2) fault localization to pinpoint problematic code segments, and (3) patch generation to produce candidate code edits. We extend this framework to include a Patch Verification phase, following Agentless, and call it SWE-SynInfer+.

## Model Performance

SWE-Reasoner has demonstrated impressive performance in software engineering tasks:

- 🌟 Achieved a **37.60% (32B) solution rate on the authoritative SWE-bench Verified** leaderboard for software engineering intelligent agents.
- 🌟 When combined with External TTC (budget=8), our model’s performance further **increases to 46.0%**.


## Quick Start
### Setup
First, create a virtual environment and install the required dependencies.
```
cd SWESynInferpro

(1) conda
conda env create -f environment.yml

(2) Mamba (Optional)
# Download and install Mamba (a faster version of conda)
curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
bash Miniforge3-$(uname)-$(uname -m).sh
source ~/.bashrc
mamba env create -f environment.yml

conda activate swesyninferpro

# Set repo_path in setup_map.json (SWESynInferpro/SWE-bench/setup_result/setup_map.json) to the local path
python scripts/1_change_testbed_path.py YOUR_ABSOLUTE_PATH/SWESynInferpro/SWE-bench/repos/testbed

(3) Git-related configuration
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

```
### Model download and deployment
```
export VLLM_USE_MODELSCOPE=True
export CUDA_VISIBLE_DEVICES=0,1

python -m vllm.entrypoints.openai.api_server \
    --gpu-memory-utilization 0.95 \
    --served-model-name SWE-Reasoner \
    --model Anonymous_Model\
    --tensor-parallel-size 2 \
    --max-model-len 131072 \
    --trust-remote-code \
    --rope-scaling '{"type": "yarn", "factor": 4.0, "original_max_position_embeddings": 32768}'


# test for deployment success
python scripts/2_call_vllm.py
```
**Please note that to avoid identity leakage, we replaced the actual model name with Anonymous_Model(not available yet), which we will replace with the actual model name after the review is finalized. Likewise, the reward model will be updated accordingly.**


### Now You can run SWE-Reasoner on SWE-bench
```
python scripts/run.py conf/vanilla-lite-swebench.conf -f
```
### Evaluation on SWE-bench
We recommend using SWE-bench docker directly for evaluation.
Refer to the [SWE-bench](https://github.com/princeton-nlp/SWE-bench) repository for more details.

#### Note: we have built-in testbed examples. After the review is completed, we will upload the entire testbed (about 130G).


## Training data
We have provided the training data for SWE-Reasoner in the **training_data/**. We use the [hiyouga/LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory) code for training. 
You can train SWE-Reasoner on your own data. 

## Acknowledgments

We would like to thank the [Qwen](https://github.com/QwenLM/Qwen2.5) team for their foundational work, which has been instrumental in the development of SWE-Reasoner.

We would also like to thank the [SWE-bench](https://github.com/princeton-nlp/SWE-bench), [AutoCodeRover](https://github.com/nus-apr/auto-code-rover), [SWESynInfer](https://github.com/LingmaTongyi/Lingma-SWE-GPT) and [Agentless](https://github.com/OpenAutoCoder/Agentless) teams for their foundational work, which played an important role in the development of SWESynInfer+.


