---
title: Open-Source CPU RTL Reading Lab
category: Computer Architecture
tags:
  - rtl
  - risc-v
  - microarchitecture
  - cva6
  - boom
  - xiangshan
  - ibex
  - rocket
  - vexriscv
date: 2026-08-01
updated: 2026-08-01
status: draft
description: A repository map and annotated RTL walkthrough across five open-source RISC-V cores (Ibex, CVA6, Rocket, BOOM, XiangShan) and one SpinalHDL core (VexRiscv), comparing how each implements the ALU, branch resolution, and register renaming, with commit-pinned source excerpts.
sources:
  - title: lowRISC Ibex
    url: https://github.com/lowRISC/ibex
    type: repo
  - title: OpenHW Group CVA6
    url: https://github.com/openhwgroup/cva6
    type: repo
  - title: Chipsalliance Rocket Chip
    url: https://github.com/chipsalliance/rocket-chip
    type: repo
  - title: RISC-V BOOM
    url: https://github.com/riscv-boom/riscv-boom
    type: repo
  - title: OpenXiangShan
    url: https://github.com/OpenXiangShan/XiangShan
    type: repo
  - title: SpinalHDL VexRiscv
    url: https://github.com/SpinalHDL/VexRiscv
    type: repo
---

## Purpose

Reading spec text tells you what a CPU must do. Reading RTL tells you how a real team chose to build it, and different teams choose differently even for the same ISA. This note is a map into six open-source RISC-V(-ish) cores, plus annotated excerpts, pinned to commit SHAs, for three concerns every core has to solve: integer ALU operations, branch resolution, and (where applicable) register renaming. The goal is a "same idea, different implementation" comparison table you can use as a jumping-off point for reading the full sources yourself.

## Repository map

| Core | Language | Style | Pipeline | Repo | Commit pinned below |
|---|---|---|---|---|---|
| Ibex | SystemVerilog | In-order, 2-stage | Fetch/Decode+Execute | [lowRISC/ibex](https://github.com/lowRISC/ibex) | `3250d994` |
| CVA6 (Ariane) | SystemVerilog | In-order, 6-stage, single-issue | Fetch, Decode, Issue, EX, WB, Commit | [openhwgroup/cva6](https://github.com/openhwgroup/cva6) | `e4184b66` |
| Rocket | Chisel | In-order, 5-stage, single-issue | Classic RISC 5-stage | [chipsalliance/rocket-chip](https://github.com/chipsalliance/rocket-chip) | `55bcad0f` |
| BOOM (v3) | Chisel | Out-of-order, superscalar | Fetch, Decode, Rename, Dispatch, Issue, EX, WB, Commit | [riscv-boom/riscv-boom](https://github.com/riscv-boom/riscv-boom) | `97bf5363` |
| XiangShan | Chisel | Out-of-order, superscalar, server-class | Similar to BOOM, deeper OoO window | [OpenXiangShan/XiangShan](https://github.com/OpenXiangShan/XiangShan) | `4ce2f88a` |
| VexRiscv | SpinalHDL (Scala DSL) | In-order, plugin-composed pipeline | Configurable stage count via plugins | [SpinalHDL/VexRiscv](https://github.com/SpinalHDL/VexRiscv) | `68075606` |

Ibex and Rocket both target small in-order cores but differ in HDL (SystemVerilog vs. Chisel). BOOM is explicitly "Berkeley Out-of-Order Machine," built as an OoO sibling to Rocket and sharing its ALU. XiangShan is the most aggressive of the six, targeting server-class IPC. VexRiscv is unusual in that its pipeline depth and stage composition are not fixed in the source; they're assembled at elaboration time from a list of plugins (`BranchPlugin`, `IntAluPlugin`, and so on), which is why its branch logic below reads more like a builder pattern than fixed RTL.

## Same idea, different implementation

### Integer ALU

Every core needs `add`, `sub`, shifts, and comparisons. All six converge on the same trick for subtraction and comparison: negate-and-add, so the same adder does both.

Ibex (`rtl/ibex_alu.sv`, commit `3250d994`) prepares the adder operands explicitly and reuses the same 33-bit adder for `SLT`/`SLTU` by inspecting the sign bits and the adder's result bit:

```systemverilog
// prepare operand b
assign operand_b_neg = {operand_b_i,1'b0} ^ {33{1'b1}};
always_comb begin
  unique case (1'b1)
    multdiv_sel_i:     adder_in_b = multdiv_operand_b_i;
    adder_op_b_negate: adder_in_b = operand_b_neg;
    default:           adder_in_b = {operand_b_i, 1'b0};
  endcase
end
// actual adder
assign adder_result_ext_o = $unsigned(adder_in_a) + $unsigned(adder_in_b);
```

Rocket's `ALU.scala` (commit `55bcad0f`, reused unmodified by BOOM) does the same negate-on-subtract trick in one line, then derives `SLT` from the adder's sign bit and an XOR of the two operand signs:

```scala
val in2_inv = Mux(isSub(io.fn), ~io.in2, io.in2)
val in1_xor_in2 = io.in1 ^ in2_inv
io.adder_out := io.in1 + in2_inv + isSub(io.fn)

val slt =
  Mux(io.in1(xLen-1) === io.in2(xLen-1), io.adder_out(xLen-1),
  Mux(cmpUnsigned(io.fn), io.in2(xLen-1), io.in1(xLen-1)))
```

The shared shape (one adder, operand-B inversion for subtract, sign-bit inspection for comparisons) is the textbook RISC ALU. What differs is bitmanip (Zbb/Zbs) support: Ibex's `ibex_alu.sv` spends most of its ~700 lines on optional `RV32B` logic (CLZ/CTZ/CPOP via a Brent-Kung-style parallel-prefix bit counter, carry-less multiply for CRC, a butterfly network for bit compress/decompress), gated behind a `RV32B` parameter so a minimal Ibex build strips all of it out. Rocket's `ALU.scala` folds its smaller Zbb subset (`FN_UNARY` for clz/ctz/cpop/orc.b/rev8, `FN_MAX`/`FN_MIN`, `FN_ROL`/`FN_ROR`) into the same `MuxLookup` as the base ops, conditionally included only `if (coreParams.useZbb)`.

### Branch resolution

CVA6 resolves branch *prediction* correctness in its frontend BHT (`core/frontend/bht.sv`, commit `e4184b66`), a direct-mapped table of 2-bit saturating counters indexed by PC:

```systemverilog
if (saturation_counter == 2'b11) begin
  if (!bht_update_i.taken)
    bht_d[update_pc][update_row_index].saturation_counter = saturation_counter - 1;
end else if (saturation_counter == 2'b00) begin
  if (bht_update_i.taken)
    bht_d[update_pc][update_row_index].saturation_counter = saturation_counter + 1;
end else begin
  if (bht_update_i.taken)
    bht_d[update_pc][update_row_index].saturation_counter = saturation_counter + 1;
  else bht_d[update_pc][update_row_index].saturation_counter = saturation_counter - 1;
end
```

This is the classic 2-bit saturating counter: two consecutive wrong guesses are required to flip the prediction, which damps single-mispredict noise. It answers "was the branch taken," not "did the branch execute correctly," which is resolved separately once the branch reaches execute.

BOOM's `ALUUnit` (`functional-unit.scala`, commit `97bf5363`) computes the actual branch outcome in the execute stage and compares it against what the frontend predicted, generating a `mispredict` signal:

```scala
val is_taken = io.req.valid && !killed &&
                (uop.is_br || uop.is_jalr || uop.is_jal) &&
                (pc_sel =/= PC_PLUS4)
when (is_br || is_jalr) {
  when (pc_sel === PC_PLUS4) { mispredict := uop.taken }
  when (pc_sel === PC_BRJMP) { mispredict := !uop.taken }
}
```

`uop.taken` here is the prediction that was stashed with the instruction back at fetch; `pc_sel` is what execute actually computed. A mismatch fires `brinfo.mispredict`, which higher-level logic uses to squash younger in-flight instructions, exactly the flush that Agner Fog's manual (cited in [[systems/operating-systems/benchmarks/branch|branch prediction benchmarks]]) prices at tens of cycles.

VexRiscv's `BranchPlugin.scala` (commit `68075606`) shows the same "predict early, correct late" shape but reifies it as a plugin, with three build modes (`buildWithoutPrediction`, `buildFetchPrediction`, `buildDecodePrediction`) selected at elaboration based on which other plugins are present. The core comparison logic, shared by all three modes, is a straightforward `funct3`-based mux:

```scala
insert(BRANCH_DO) := input(BRANCH_CTRL).mux(
  BranchCtrlEnum.INC  -> False,
  BranchCtrlEnum.JAL  -> True,
  BranchCtrlEnum.JALR -> True,
  BranchCtrlEnum.B    -> input(INSTRUCTION)(14 downto 12).mux(
    B"000"  -> eq  ,
    B"001"  -> !eq  ,
    B"101"  -> !less,
    B"111"  -> !less,
    default -> less
  )
)
```

The three cores agree on the underlying arithmetic (equal/less-than comparators feeding a funct3-indexed mux) and disagree entirely on how prediction and correction are staged across the pipeline, because that staging is inseparable from how many pipeline stages each core has.

### Register renaming

This is the sharpest split in the set. Ibex, CVA6, Rocket, and VexRiscv are all in-order and have no rename stage; the architectural register file is the only register file. BOOM and XiangShan are out-of-order and both need a rename stage to remove false (WAW/WAR) dependencies before instructions enter the out-of-order window, but they use different renaming schemes:

- BOOM uses a unified physical register file, so integer, floating point, and (if present) vector rename maps live in tables mapping architectural to physical register indices, with a free list of unallocated physical registers.
- XiangShan's rename directory (`src/main/scala/xiangshan/backend/rename/`, commit `4ce2f88a`) splits the concern into separate files: `RenameTable.scala` for the architectural-to-physical map, `BusyTable.scala` for tracking which physical registers still have in-flight producers, `Snapshot.scala` for checkpointing rename state at branches (so a mispredict can roll the map back without replaying every rename), and `CompressUnit.scala`, unique among these six cores, for compressing multiple renames of the same architectural register within one superscalar rename bundle into a single effective rename before touching the free list.

The `CompressUnit` split is worth pulling on if you read one file from this whole list: renaming N instructions per cycle, where several might write the same architectural register, requires resolving intra-bundle WAW hazards before the rename table update, and XiangShan makes that a standalone unit instead of folding it into the main `Rename.scala` control logic.

## How to read further

Clone the relevant repo at the pinned commit (or use GitHub's blob view with the commit SHA in the URL, which is what the excerpts above link to implicitly through their SHA-pinned paths) rather than `HEAD`, since all six repos are under active development and line numbers drift fast. Start from the functional unit or ALU file for the easiest orientation, then follow module instantiations upward into the pipeline stage that owns it. The `SupportedFuncUnits`/`FUConstants` pattern in BOOM's `functional-unit.scala` is a good map of what functional units a superscalar core needs at minimum: ALU, jump, memory address, integer mul, integer div, CSR, FPU, FP div, int-to-FP, FP-to-int.

## Edge cases and limits

Commit SHAs pin exact source text, but these projects move fast; treat every excerpt above as "true as of that commit," not as the current state of the file. CVA6's BHT file has a large FPGA-target branch (`gen_fpga_bht`) that this note skips entirely in favor of the simpler ASIC-target branch, since the FPGA path exists only to work around synchronous-BRAM read/write timing and adds no new algorithmic content. VexRiscv's plugin system means the "pipeline" you read about in `BranchPlugin.scala` doesn't exist as a fixed set of stages anywhere in the source; it's assembled from a configuration list elsewhere in a given SoC build, so reading one plugin in isolation only shows half the picture.

## Sources

- [lowRISC Ibex](https://github.com/lowRISC/ibex), `rtl/ibex_alu.sv` at commit `3250d994`
- [OpenHW Group CVA6](https://github.com/openhwgroup/cva6), `core/frontend/bht.sv` at commit `e4184b66`
- [chipsalliance Rocket Chip](https://github.com/chipsalliance/rocket-chip), `src/main/scala/rocket/ALU.scala` at commit `55bcad0f`
- [riscv-boom/riscv-boom](https://github.com/riscv-boom/riscv-boom), `src/main/scala/v3/exu/execution-units/functional-unit.scala` at commit `97bf5363`
- [OpenXiangShan/XiangShan](https://github.com/OpenXiangShan/XiangShan), `src/main/scala/xiangshan/backend/rename/` at commit `4ce2f88a`
- [SpinalHDL/VexRiscv](https://github.com/SpinalHDL/VexRiscv), `src/main/scala/vexriscv/plugin/BranchPlugin.scala` at commit `68075606`

## Related notes

- [[hardware/computer-architecture/simd-vectors-gpus-accelerators|From SIMD to SIMT]]
- [[hardware/digital-design/371/algorithmic-state-machines|Algorithmic State Machines]]
- [[hardware/digital-design/369/system-verilog|SystemVerilog]]
- [[systems/operating-systems/benchmarks/branch|Branch Prediction Benchmarks]]
- [[hardware/computer-architecture/experiments-and-benchmarking|Experiments and Benchmarking in Computer Architecture]]
