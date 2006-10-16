Summary: A graphical interface for configuring kernel crash dumping
Name: system-config-kdump
Version: 1.0.1
Release: 3
URL: http://fedora.redhat.com/projects/config-tools/
License: GPL
ExclusiveOS: Linux
Group: System Environment/Base
BuildRoot: %{_tmppath}/%{name}-%{version}-root
BuildArch: noarch
Source0: %{name}-%{version}.tar.bz2
ExcludeArch: s390 s390x
BuildRequires: desktop-file-utils
BuildRequires: intltool
Requires: pygtk2 >= 2.8.6
Requires: pygtk2-libglade
Requires: python2
Requires: usermode >= 1.36
Requires: rhpl >= 0.185-1
Requires: redhat-artwork >= 0.61-1
Requires: kexec-tools
Prereq: gtk2 >= 2.8.20
#PreReq: hicolor-icon-theme

%description
system-config-kdump is a graphical tool for configuring kernel crash
dumping via kdump and kexec.

%prep
%setup -q

%build
make

%install
make INSTROOT=$RPM_BUILD_ROOT install
desktop-file-install --vendor system --delete-original       \
  --dir $RPM_BUILD_ROOT%{_datadir}/applications             \
  --add-category X-Red-Hat-Base                             \
  $RPM_BUILD_ROOT%{_datadir}/applications/system-config-kdump.desktop

#%find_lang %name

%clean
rm -rf $RPM_BUILD_ROOT

%preun
if [ -d /usr/share/system-config-kdump ] ; then
  rm -rf /usr/share/system-config-kdump/*.pyc
fi

#%postun
#touch --no-create %{_datadir}/icons/hicolor
#if [ -x /usr/bin/gtk-update-icon-cache ]; then
#  gtk-update-icon-cache -q %{_datadir}/icons/hicolor
#fi

#%post
#touch --no-create %{_datadir}/icons/hicolor
#if [ -x /usr/bin/gtk-update-icon-cache ]; then
#  gtk-update-icon-cache -q %{_datadir}/icons/hicolor
#fi


#%files -f %{name}.lang
%files
%defattr(-,root,root)
%{_bindir}/system-config-kdump
%{_datadir}/system-config-kdump
%{_datadir}/applications/*
%attr(0644,root,root) %config /etc/security/console.apps/system-config-kdump
%attr(0644,root,root) %config /etc/pam.d/system-config-kdump
#%attr(0644,root,root) %{_datadir}/icons/hicolor/48x48/apps/system-config-display.png

%changelog
* Mon Oct 16 2006 Dave Lehman <dlehman@redhat.com> 1.0.1-3
- Fix parsing of "crashkernel=..." string from /proc/cmdline

* Tue Oct 10 2006 Dave Lehman <dlehman@redhat.com> 1.0.1-1
- Fix bugs in writeDumpConfig and writeBootloaderConfig
- Fix handling of pre-existing "ifc" and "default" directives
- Always leave network interface checkbutton sensitive
- Various minor fixes

* Fri Oct 06 2006 Dave Lehman <dlehman@redhat.com> 1.0.0-1
- Initial build

