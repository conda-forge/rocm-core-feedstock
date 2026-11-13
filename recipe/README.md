# ROCm packaging conventions on conda-forge

Conventions shared by the ROCm feedstocks (maintained by the
`conda-forge/rocm-core` team). Discussion and decisions live in the linked
issues; this file is the short version for recipe authors and reviewers.

## Version anchor: `rocm-core` in `host`

ROCm gives no ABI guarantee across minor releases, and every upstream
component depends on `rocm-core` for that reason. On conda-forge the same
policy lives in one place, `rocm-core`'s run export
(`pin_subpackage(name, upper_bound='x.x')`).

Every ROCm recipe therefore lists

```yaml
host:
  # rocm-core is a host dependency by convention, see
  # https://github.com/conda-forge/rocm-core-feedstock/issues/21
  - rocm-core ${{ version }}.*
```

even when nothing links against it. The run export turns this into
`rocm-core >=7.2.4,<7.3.0a0` in the package's run requirements. Do not move
it to `run` with a hand-written range: that duplicates the policy in every
feedstock and loses the exact lower bound. The rattler-build "overdepending"
warning this produces is known; see
[#21](https://github.com/conda-forge/rocm-core-feedstock/issues/21) for the
planned `rocm-core` / `librocm-core` split that removes it.

## Version bot: restrict tags to `rocm-*`

The `rocm-systems` and `rocm-libraries` monorepos carry, next to the
`rocm-X.Y.Z` release tags, `therock-*` release tags and a steady stream of
`hip-version_*` build tags. The conda-forge version bot takes the highest tag
it finds, cannot download it under the `rocm-<version>` URL template, and
stops proposing updates altogether. Every feedstock sourced from these
repositories (and from the archived per-component repositories, which have
stray test and date tags) sets in `conda-forge.yml`:

```yaml
bot:
  version_updates:
    allowed_tag_globs: "rocm-*"
```

When the stack moves to the TheRock-based releases, the glob changes together
with the source URLs. `recipe/tools/rocm-bot-audit.py` in this repository checks all
ROCm feedstocks against the bot's data store and flags the ones where the bot
is stuck; run it after adding a feedstock, or whenever updates seem to have
stopped arriving:

```sh
python3 recipe/tools/rocm-bot-audit.py
```

## Compiler: `compiler('hip')` and local clang pins

`{{ compiler('hip') }}` comes from the global pinning
(`hip_compiler: hip-rocm-clang`, `hip_compiler_version: [None, 7.2]`,
[conda-forge-pinning#9043](https://github.com/conda-forge/conda-forge-pinning-feedstock/pull/9043)).
Recipes that support both CUDA and HIP skip the combination with
`hip_compiler_version != "None" and cuda_compiler_version != "None"`.

Recipes that need clang as the host C++ compiler next to the HIP compiler pin
it to the LLVM major of the ROCm release in their own
`recipe/conda_build_config.yaml` (for ROCm 7.2: `clang_compiler_version: ["22"]`,
`clangxx_compiler_version: ["22"]`). There is deliberately no global zip of
the clang and HIP versions: the global clang pin moves about once a year and
ROCm's LLVM fork tracks LLVM main, so the two would drift anyway.

## Layout: `lib<name>` / `lib<name>-devel` / `<name>`

Library feedstocks follow the split used by
[rock-the-conda](https://github.com/gbionics/rock-the-conda): `lib<name>` with
the shared library (run export with `upper_bound='x.x'`), `lib<name>-devel`
with headers and CMake files, and a `<name>` metapackage. New outputs need to
be registered through
[admin-requests](https://github.com/conda-forge/admin-requests) before the
feedstock can publish them.
