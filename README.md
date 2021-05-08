# Fedora Kernel Build Scripts

Build scripts for building a Fedora kernel package from a (potentially dirty) work tree, intended for (faster) kernel development. Supports cross-compiling for aarch64.

Do not use this for proper package releases.

## Usage

1. Clone/symlink/copy kernel source tree to the `kernel/` directory.
2. Configure your kernel (e.g. run `make config` inside `kernel/` or copy config to `kernel/.config).
3. Build packages via `./makerpm`. For cross-compiling from x86 to aarch64, run `./makerpm -- --with-cross --target aarch64-linux-gnu`.

and for development

4. Make changes to the kernel source.
5. Go to step 3 to build updated packages.

## Credits

Based on the work of [Dorian Stoll](https://github.com/stolld/) for [linux-surface](https://github.com/linux-surface/linux-surface).

