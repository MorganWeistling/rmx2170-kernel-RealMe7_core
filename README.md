# RMX2170 Kernel — KernelSU-Next + SUSFS

One-click GitHub Actions build of a custom **4.14** kernel for the
**Realme 7 Pro (RMX2170, atoll / Snapdragon 720G)** with
**KernelSU-Next** root and **SUSFS** hiding, packaged as an AnyKernel3
flashable zip.

> ⚠️ Requires an **unlocked bootloader**. Flashing a custom kernel on a
> locked device will fail / soft-brick.

## Verified stack

| Piece | Value |
|---|---|
| Kernel source | `sm7125/android_kernel_realme_sm7125` branch `aex9` |
| defconfig | `vendor/atoll-perf_defconfig` |
| Root | KernelSU-Next (`next`) |
| Hiding | SUSFS `kernel-4.14` |
| Toolchain | Proton clang |
| Packaging | AnyKernel3 (`block=auto`, A/B slot device) |

## Use

1. Create a new **GitHub repo** and push this folder:
   ```bash
   cd rmx2170-kernel
   git init && git add . && git commit -m "RMX2170 kernel CI"
   git branch -M main
   git remote add origin https://github.com/<you>/rmx2170-kernel.git
   git push -u origin main
   ```
2. GitHub → **Actions** → *Build RMX2170 Kernel* → **Run workflow**.
   Toggle KernelSU-Next / SUSFS or change branch/defconfig if needed.
3. Download the `RMX2170-KSUNext-SUSFS-*.zip` artifact when the run finishes.

## Flash

- Reboot to a custom recovery (TWRP/OFOX for atoll) and install the zip, **or**
- `fastboot boot` a patched boot to test first.

After first boot, install the **KernelSU-Next Manager** app and enable SUSFS
modules from there.

## If the SUSFS patch shows rejects

The build logs a `::warning::` and leaves `*.rej` files. The most common cause
is a susfs release whose `50_add_susfs_in_kernel-4.14.patch` drifted from this
tree. Pin a specific susfs tag by editing the *Apply SUSFS patches* step, or
build KSU-Next-only first (toggle SUSFS off) to confirm the base compiles.

## Notes

- The kernel source branch `aex9` is a LineageOS/AEX-style tree. Other bases
  exist (`crdroidandroid/android_kernel_realme_sm7125`,
  `mello-kernel/kernel_realme_sm7125`, `Evolution-X-Devices/kernel_realme_sm7125`)
  — swap `kernel_repo` / `kernel_branch` inputs to use them.
- If `Image.gz-dtb` isn't produced, the workflow falls back to `Image-dtb` /
  `Image.gz` automatically.
