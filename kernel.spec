%global kernel_version 5.12.0
%global kernel_release 1
%global kernel_basename surface-dev

%global fedora_title_fc34 34 (Thirty Four)
%global fedora_title_fc33 33 (Thirty Three)

%global fedora_title %{fedora_title_fc%{fedora}}

%global kernel_extver %(echo %{kernel_basename} | sed -e 's/-/_/g')
%global package_name kernel-%{kernel_basename}
%global kernel_majorversion %(echo %{kernel_version} | cut -d'.' -f1-2)
%global kernel_localversion %{kernel_release}.%{kernel_extver}%{?dist}.%{_target_cpu}
%global kernel_name %{kernel_version}-%{kernel_localversion}
%global kernel_modpath %{buildroot}/lib/modules/%{kernel_name}

%global debug_package %{nil}
%global _build_id_links alldebug


%bcond_with cross


Name:       %{package_name}
Summary:    Development kernel for Microsoft Surface devices
Version:    %{kernel_version}
Release:    %{kernel_release}%{?dist}
License:    GPLv2
URL:        https://github.com/linux-surface/kernel

Provides: installonlypkg(%{package_name})
Provides: kernel-uname-r = %{kernel_name}
Provides: kernel-core-uname-r = %{kernel_name}
Provides: kernel-modules-uname-r = %{kernel_name}

Requires(pre): coreutils, systemd >= 203-2, /usr/bin/kernel-install
Requires(pre): dracut >= 027
Requires(pre): linux-firmware >= 20150904-56.git6ebf5d57
Requires(preun): systemd >= 200

BuildRequires: openssl openssl-devel
BuildRequires: kmod, patch, bash, tar, git-core, sbsigntools
BuildRequires: bzip2, xz, findutils, gzip, m4, perl-interpreter,
BuildRequires: perl-Carp, perl-devel, perl-generators, make, diffutils,
BuildRequires: gawk, gcc, binutils, redhat-rpm-config, hmaccalc, bison
BuildRequires: flex, net-tools, hostname, bc, elfutils-devel
BuildRequires: gcc-plugin-devel dwarves

# Used to mangle unversioned shebangs to be Python 3
BuildRequires: python3-devel

Conflicts: xfsprogs < 4.3.0-1
Conflicts: xorg-x11-drv-vmmouse < 13.0.99
BuildConflicts: rhbuildsys(DiskFree) < 500Mb
BuildConflicts: rpm < 4.13.0.1-19
BuildConflicts: dwarves < 1.13

Source100:  mod-sign.sh
Source101:  parallel_xz.sh

ExclusiveArch: x86_64 aarch64

%if %{with cross}
BuildRequires: binutils-%{_build_arch}-linux-gnu, gcc-%{_build_arch}-linux-gnu
%define cross_opts CROSS_COMPILE=%{_build_arch}-linux-gnu-
%define __strip %{_build_arch}-linux-gnu-strip
%endif

%ifarch x86_64
%define kernel_arch x86_64
%endif

%ifarch aarch64
%define kernel_arch arm64
%endif

%description
Development kernel for Microsoft Surface devices

%package devel
Summary: Development package for building kernel modules for %{package_name}
AutoReqProv: no
Provides: installonlypkg(%{package_name})
Provides: kernel-devel-uname-r = %{kernel_name}

%description devel
This package provides kernel headers and makefiles sufficient to build modules
against the %{package_name} package.

%prep
cd kernel

echo $((%{kernel_release} - 1)) > .version

# This Prevents scripts/setlocalversion from mucking with our version numbers.
touch .scmversion

# Mangle /usr/bin/python shebangs to /usr/bin/python3
# Mangle all Python shebangs to be Python 3 explicitly
# -p preserves timestamps
# -n prevents creating ~backup files
# -i specifies the interpreter for the shebang
# This fixes errors such as
# *** ERROR: ambiguous python shebang in /usr/bin/kvm_stat: #!/usr/bin/python. Change it to python3 (or python2) explicitly.
# We patch all sources below for which we got a report/error.
pathfix.py -i "%{__python3} %{py3_shbang_opts}" -p -n \
	tools/kvm/kvm_stat/kvm_stat \
	scripts/show_delta \
	scripts/diffconfig \
	scripts/bloat-o-meter \
	scripts/jobserver-exec \
	tools \
	Documentation \
	scripts/clang-tools

%build
cd kernel

%{__make} %{?_smp_mflags} olddefconfig LOCALVERSION=-%{kernel_localversion} ARCH=%{kernel_arch} %{?cross_opts}
%{__make} %{?_smp_mflags} all LOCALVERSION=-%{kernel_localversion} ARCH=%{kernel_arch} %{?cross_opts}

%define __modsign_install_post \
  %{SOURCE100} certs/signing_key.pem certs/signing_key.x509 %{kernel_modpath} \
  find %{kernel_modpath} -type f -name '*.ko' | %{SOURCE101} %{?_smp_mflags}; \
%{nil}

#
# Disgusting hack alert! We need to ensure we sign modules *after* all
# invocations of strip occur.
#
%define __spec_install_post \
  %{?__debug_package:%{__debug_install_post}}\
  %{__arch_install_post}\
  %{__os_install_post}\
  %{__modsign_install_post}

%install
cd kernel

mkdir -p %{buildroot}/boot

# Install modules
%{__make} %{?_smp_mflags} INSTALL_MOD_PATH=%{buildroot} modules_install KERNELRELEASE=%{kernel_name} ARCH=%{kernel_arch} %{?cross_opts}

# Install vmlinuz
image_name=$(%{__make} %{?_smp_mflags} -s image_name LOCALVERSION=-%{kernel_localversion} ARCH=%{kernel_arch} %{?cross_opts})
install -m 755 $image_name %{buildroot}/boot/vmlinuz-%{kernel_name}
install -m 755 $image_name %{kernel_modpath}/vmlinuz

# Install System.map and .config
install -m 644 System.map %{kernel_modpath}/System.map
install -m 644 System.map %{buildroot}/boot/System.map-%{kernel_name}
install -m 644 .config %{kernel_modpath}/config
install -m 644 .config %{buildroot}/boot/config-%{kernel_name}

# hmac sign the kernel for FIPS
sha512hmac %{buildroot}/boot/vmlinuz-%{kernel_name} | sed -e "s,%{buildroot},," > %{kernel_modpath}/.vmlinuz.hmac
cp %{kernel_modpath}/.vmlinuz.hmac %{buildroot}/boot/.vmlinuz-%{kernel_name}.hmac

# mark modules executable so that strip-to-file can strip them
find %{kernel_modpath} -name "*.ko" -type f | xargs --no-run-if-empty chmod u+x

# Setup directories for -devel files
rm -f %{kernel_modpath}/build
rm -f %{kernel_modpath}/source
mkdir -p %{kernel_modpath}/build
pushd %{kernel_modpath}
	ln -s build source
popd

# first copy everything
cp --parents $(find  -type f -name "Makefile*" -o -name "Kconfig*") %{kernel_modpath}/build
cp Module.symvers %{kernel_modpath}/build
cp System.map %{kernel_modpath}/build
if [ -s Module.markers ]; then
	cp Module.markers %{kernel_modpath}/build
fi

# then drop all but the needed Makefiles/Kconfig files
rm -rf %{kernel_modpath}/build/scripts
rm -rf %{kernel_modpath}/build/include
cp .config %{kernel_modpath}/build
cp -a scripts %{kernel_modpath}/build
rm -rf %{kernel_modpath}/build/scripts/tracing
rm -f %{kernel_modpath}/build/scripts/spdxcheck.py

if [ -f tools/objtool/objtool ]; then
	cp -a tools/objtool/objtool %{kernel_modpath}/build/tools/objtool/ || :

	# these are a few files associated with objtool
	cp -a --parents tools/build/Build.include %{kernel_modpath}/build/
	cp -a --parents tools/build/Build %{kernel_modpath}/build/
	cp -a --parents tools/build/fixdep.c %{kernel_modpath}/build/
	cp -a --parents tools/scripts/utilities.mak %{kernel_modpath}/build/

	# also more than necessary but it's not that many more files
	cp -a --parents tools/objtool/* %{kernel_modpath}/build/
	cp -a --parents tools/lib/str_error_r.c %{kernel_modpath}/build/
	cp -a --parents tools/lib/string.c %{kernel_modpath}/build/
	cp -a --parents tools/lib/subcmd/* %{kernel_modpath}/build/
fi

if [ -d arch/%{kernel_arch}/scripts ]; then
	cp -a arch/%{kernel_arch}/scripts %{kernel_modpath}/build/arch/%{kernel_arch}/ || :
fi

if [ -f arch/%{kernel_arch}/*lds ]; then
	cp -a arch/%{kernel_arch}/*lds %{kernel_modpath}/build/arch/%{kernel_arch}/ || :
fi

if [ -f arch/%{kernel_arch}/kernel/module.lds ]; then
	cp -a --parents arch/%{kernel_arch}/kernel/module.lds %{kernel_modpath}/build/
fi

rm -f %{kernel_modpath}/build/scripts/*.o
rm -f %{kernel_modpath}/build/scripts/*/*.o

if [ -d arch/%{kernel_arch}/include ]; then
	cp -a --parents arch/%{kernel_arch}/include %{kernel_modpath}/build/
fi

cp -a include %{kernel_modpath}/build/include

# files for 'make prepare' to succeed with kernel-devel
%ifarch x86_64
cp -a --parents arch/x86/entry/syscalls/syscall_32.tbl %{kernel_modpath}/build/
cp -a --parents arch/x86/entry/syscalls/syscalltbl.sh %{kernel_modpath}/build/
cp -a --parents arch/x86/entry/syscalls/syscallhdr.sh %{kernel_modpath}/build/
cp -a --parents arch/x86/entry/syscalls/syscall_64.tbl %{kernel_modpath}/build/
cp -a --parents arch/x86/tools/relocs_32.c %{kernel_modpath}/build/
cp -a --parents arch/x86/tools/relocs_64.c %{kernel_modpath}/build/
cp -a --parents arch/x86/tools/relocs.c %{kernel_modpath}/build/
cp -a --parents arch/x86/tools/relocs_common.c %{kernel_modpath}/build/
cp -a --parents arch/x86/tools/relocs.h %{kernel_modpath}/build/
%endif

# Yes this is more includes than we probably need. Feel free to sort out
# dependencies if you so choose.
cp -a --parents tools/include/* %{kernel_modpath}/build/
%ifarch x86_64
cp -a --parents arch/x86/purgatory/purgatory.c %{kernel_modpath}/build/
cp -a --parents arch/x86/purgatory/stack.S %{kernel_modpath}/build/
cp -a --parents arch/x86/purgatory/setup-x86_64.S %{kernel_modpath}/build/
cp -a --parents arch/x86/purgatory/entry64.S %{kernel_modpath}/build/
cp -a --parents arch/x86/boot/string.h %{kernel_modpath}/build/
cp -a --parents arch/x86/boot/string.c %{kernel_modpath}/build/
cp -a --parents arch/x86/boot/ctype.h %{kernel_modpath}/build/
%endif

# Make sure the Makefile and version.h have a matching timestamp so that
# external modules can be built
touch -r %{kernel_modpath}/build/Makefile %{kernel_modpath}/build/include/generated/uapi/linux/version.h

# Copy .config to include/config/auto.conf so "make prepare" is unnecessary.
cp %{kernel_modpath}/build/.config %{kernel_modpath}/build/include/config/auto.conf

mkdir -p %{buildroot}/usr/src/kernels
mv %{kernel_modpath}/build %{buildroot}/usr/src/kernels/%{kernel_name}

# This is going to create a broken link during the build, but we don't use
# it after this point.  We need the link to actually point to something
# when kernel-devel is installed, and a relative link doesn't work across
# the F17 UsrMove feature.
ln -sf /usr/src/kernels/%{kernel_name} %{kernel_modpath}/build

# prune junk from kernel-devel
find %{buildroot}/usr/src/kernels -name ".*.cmd" -delete

# remove files that will be auto generated by depmod at rpm -i time
pushd %{kernel_modpath}
	rm -f modules.{alias*,builtin.bin,dep*,*map,symbols*,devname,softdep}
popd

# build a BLS config for this kernel
cat >%{kernel_modpath}/bls.conf <<EOF
title Fedora (%{kernel_name}) %{fedora_title}
version %{kernel_name}
linux /vmlinuz-%{kernel_name}
initrd /initramfs-%{kernel_name}.img
options \$kernelopts
grub_users \$grub_users
grub_arg --unrestricted
grub_class kernel
EOF

%clean
rm -rf %{buildroot}

%post
/bin/kernel-install add %{kernel_name} /lib/modules/%{kernel_name}/vmlinuz || exit $?

%preun
/bin/kernel-install remove %{kernel_name} /lib/modules/%{kernel_name}/vmlinuz || exit $?

%files
%defattr (-, root, root)
/lib/modules/%{kernel_name}
%ghost /boot/vmlinuz-%{kernel_name}
%ghost /boot/config-%{kernel_name}
%ghost /boot/System.map-%{kernel_name}
%ghost /boot/.vmlinuz-%{kernel_name}.hmac

%files devel
%defattr (-, root, root)
/usr/src/kernels/%{kernel_name}

