# Quantization-Only Appendix Materials

This file reorganizes the RotateTileKV quantization-only results into appendix-ready materials for `samplepaper.tex`.

## 0. Data Sources

- `D:\Git\mustafar\RotateTileKV\LLAMA3_8B_CURRENT_RESULTS.md`
- `D:\Git\mustafar\RotateTileKV\LLAMA2_7B_CURRENT_RESULTS.md`
- `D:\Git\mustafar\RotateTileKV\MISTRAL_7B_V01_CURRENT_RESULTS.md`
- `D:\Git\mustafar\RotateTileKV\QWEN25_7B_INSTRUCT_CURRENT_RESULTS.md`
- `D:\Git\mustafar\RotateTileKV\ALL_MODELS_CURRENT_RESULTS.md`

## 1. Protocol Card

### 1.1 Study Goal

- Isolate the quantization component from the sparse policy.
- Compare a KIVI-style quantizer against the quantizer used by JSQKV.
- Use the RotateTileKV harness as the quantization-only proxy of the JSQKV quantizer.

### 1.2 Matched Settings

`KIVI-style` baseline:

- `quant_impl = kivi`
- `k_quant_scheme = kivi-channel`
- `v_quant_scheme = per-token-head`
- `group_size = 128`
- `quant_granularity = per-token-tile`
- `residual_length = 128`
- Hadamard disabled

`JSQKV quantizer proxy`:

- per-token-tile quantization
- `tile_size = 64`
- tile Hadamard enabled
- `hadamard_group_size = 64`
- `residual_length = 128`

### 1.3 Paper Wording

- Recommended wording: "quantization-only comparison"
- Recommended method names in tables:
  - `KIVI-style`
  - `JSQKV quantizer`

## 2. Table Titles

### 2.1 Main Appendix Table Title

Use:

> Quantization-only comparison on Meta-Llama-3-8B-Instruct. `JSQKV quantizer` denotes per-token-tile quantization with tile Hadamard(64) and residual length 128. Avg. is the full 16-task LongBench average.

### 2.2 Cross-Model Table Title

Use:

> Cross-model averages for the quantization-only comparison. Llama-3-8B-Instruct and Llama-2-7B use full LongBench; Mistral-7B-v0.1 and Qwen2.5-7B-Instruct use the six-task selected subset. `Delta` is `JSQKV quantizer minus KIVI-style`.

## 3. Ready-to-Use Tables

### 3.1 Meta-Llama-3-8B-Instruct Full LongBench

| Setting | Bit | NarrativeQA | HotpotQA | GovReport | TREC | PCount | LCC | Avg. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| KIVI-style | 4-bit | 24.26 | 46.06 | 29.53 | 74.00 | 6.50 | 54.07 | 42.87 |
| JSQKV quantizer | 4-bit | 22.47 | 46.07 | 30.03 | 73.50 | 5.50 | 57.20 | 42.72 |
| KIVI-style | 3-bit | 20.81 | 45.64 | 29.35 | 74.00 | 6.75 | 60.94 | 41.80 |
| JSQKV quantizer | 3-bit | 21.64 | 46.62 | 29.16 | 73.50 | 7.00 | 53.66 | 41.48 |
| KIVI-style | 2-bit | 16.55 | 27.50 | 23.91 | 58.00 | 2.00 | 27.03 | 26.94 |
| JSQKV quantizer | 2-bit | 17.90 | 37.93 | 25.63 | 55.50 | 3.00 | 30.37 | 30.59 |

### 3.2 Cross-Model Summary

| Model | Protocol | KIVI 4-bit | JSQKV 4-bit | Delta | KIVI 3-bit | JSQKV 3-bit | Delta | KIVI 2-bit | JSQKV 2-bit | Delta |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Meta-Llama-3-8B-Instruct | full LongBench | 42.87 | 42.72 | -0.15 | 41.80 | 41.48 | -0.32 | 26.94 | 30.59 | +3.65 |
| Llama-2-7B | full LongBench | 28.09 | 28.33 | +0.24 | 28.23 | 27.82 | -0.41 | 24.33 | 24.17 | -0.16 |
| Mistral-7B-v0.1 | selected6 | 31.19 | 30.78 | -0.41 | 30.16 | 29.52 | -0.64 | 23.91 | 25.72 | +1.81 |
| Qwen2.5-7B-Instruct | selected6 | 14.47 | 3.53 | -10.94 | 10.94 | 1.76 | -9.18 | 8.13 | 2.04 | -6.09 |

## 4. Result Bullets

### 4.1 Main Numeric Takeaways

- Meta-Llama-3-8B-Instruct:
  - 4-bit: `42.87` vs `42.72`, nearly tied
  - 3-bit: `41.80` vs `41.48`, nearly tied
  - 2-bit: `26.94` vs `30.59`, JSQKV quantizer `+3.65`
- Llama-2-7B:
  - 4-bit: JSQKV quantizer `+0.24`
  - 3-bit: KIVI-style `+0.41`
  - 2-bit: KIVI-style `+0.16`
- Mistral-7B-v0.1:
  - 4-bit: KIVI-style `+0.41`
  - 3-bit: KIVI-style `+0.64`
  - 2-bit: JSQKV quantizer `+1.81`
- Qwen2.5-7B-Instruct:
  - KIVI-style is clearly better at all three bit widths

### 4.2 Task-Level Highlight on Meta-Llama-3-8B-Instruct

- At 2-bit, the most visible gains for the JSQKV quantizer are:
  - `HotpotQA`: `37.93` vs `27.50`
  - `GovReport`: `25.63` vs `23.91`
  - `LCC`: `30.37` vs `27.03`

## 5. Appendix Paragraph Options

### 5.1 Tight Version

> To isolate the numerical representation used by JSQKV from the sparse policy, we additionally compare a quantization-only instantiation of the JSQKV quantizer against a matched KIVI-style baseline. On Meta-Llama-3-8B-Instruct, the two methods are nearly tied at 4-bit and 3-bit, but the JSQKV quantizer becomes clearly stronger at 2-bit, improving the full-benchmark average from 26.94 to 30.59. Cross-model results show the same low-bit trend on Mistral-7B-v0.1, while Llama-2-7B remains roughly tied and Qwen2.5-7B-Instruct remains a negative case. These results suggest that the main benefit of the JSQKV quantizer is improved robustness in aggressive low-bit settings rather than a uniform advantage across all model families.

### 5.2 Slightly Fuller Version

> We further report a quantization-only comparison to isolate the low-bit numerical representation from the sparse policy. The KIVI-style baseline remains slightly stronger at 4-bit and 3-bit on some model families, but the JSQKV quantizer becomes more competitive as the precision budget tightens and is clearly stronger at 2-bit on Meta-Llama-3-8B-Instruct and Mistral-7B-v0.1. This pattern indicates that the tile-aligned Hadamard design is particularly helpful in the aggressive low-bit regime, while also showing that its cross-model robustness is not yet uniform.

## 6. Citation-Ready Claim Sentences

### 6.1 Conservative Claim

> The quantization component used by JSQKV is competitive with a matched KIVI-style baseline on Llama-family models and becomes stronger in the most aggressive 2-bit setting on Meta-Llama-3-8B-Instruct.

### 6.2 Balanced Claim

> The quantizer used by JSQKV does not uniformly dominate KIVI-style quantization across all model families, but it shows a clear robustness advantage in aggressive 2-bit settings on Meta-Llama-3-8B-Instruct and Mistral-7B-v0.1.

### 6.3 Stronger Claim for Appendix Only

> These results support the view that the main contribution of the JSQKV quantizer is not a universal gain at mild bit widths, but improved low-bit stability when the numerical budget becomes tight.

## 7. Negative-Case Sentences

### 7.1 Qwen-Friendly Wording

> Qwen2.5-7B-Instruct remains a clear negative case, indicating that the current tile-wise rotated quantizer is not yet uniformly robust across model families.

### 7.2 More Neutral Wording

> The comparison also reveals a model-family gap: while the proposed quantizer is competitive on Llama and Mistral, it remains substantially weaker on Qwen2.5-7B-Instruct.

## 8. Recommended Final Appendix Composition

01. One short protocol paragraph  
02. One paragraph interpreting the Meta-Llama-3-8B-Instruct table  
03. One paragraph interpreting the cross-model table  
04. Keep only two tables in the paper:
- the detailed Llama-3 table
- the cross-model summary table
05. Keep task-level tables for Llama-2/Mistral/Qwen only in this `md` material file, not in the main appendix, unless space allows

## 9. Suggested Final Paper Message

- Do say:
  - "nearly tied at 4-bit and 3-bit"
  - "clearly stronger at 2-bit on Meta-Llama-3-8B-Instruct"
  - "improved low-bit robustness"
  - "not uniform across all model families"
- Do not say:
  - "consistently outperforms KIVI"
  - "generalizes across all architectures"
  - "universally superior quantizer"
