Summary: A graphical interface for configuring kernel crash dumping
Name: system-config-kdump
Version: 1.0.12
Release: 1%{?dist}
URL: http://fedora.redhat.com/projects/config-tools/
License: GPL2+
Group: System Environment/Base
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch
Source0: %{name}-%{version}.tar.bz2
ExcludeArch: s390 s390x
BuildRequires: desktop-file-utils
BuildRequires: intltool, gettext
Requires: pygtk2 >= 2.8.6
Requires: pygtk2-libglade
Requires: usermode >= 1.36
Requires: rhpl >= 0.185-1
Requires: redhat-artwork >= 0.61-1
Requires: kexec-tools
Requires(pre): gtk2 >= 2.8.20
Requires(pre): hicolor-icon-theme

%description
system-config-kdump is a graphical tool for configuring kernel crash
dumping via kdump and kexec.

%prep
%setup -q

%build
make

%install
rm -rf $RPM_BUILD_ROOT
make INSTROOT=$RPM_BUILD_ROOT install
desktop-file-install --vendor system --delete-original       \
  --dir $RPM_BUILD_ROOT%{_datadir}/applications             \
  --add-category X-Red-Hat-Base                             \
  $RPM_BUILD_ROOT%{_datadir}/applications/system-config-kdump.desktop

%find_lang %{name}

%clean
rm -rf $RPM_BUILD_ROOT

%postun
touch --no-create %{_datadir}/icons/hicolor
if [ -x /usr/bin/gtk-update-icon-cache ]; then
  gtk-update-icon-cache -q %{_datadir}/icons/hicolor
fi

%post
touch --no-create %{_datadir}/icons/hicolor
if [ -x /usr/bin/gtk-update-icon-cache ]; then
  gtk-update-icon-cache -q %{_datadir}/icons/hicolor
fi


%files -f %{name}.lang
%defattr(-,root,root,-)
%{_bindir}/system-config-kdump
%{_datadir}/system-config-kdump
%{_datadir}/applications/*
%config(noreplace) %{_sysconfdir}/security/console.apps/system-config-kdump
%config(noreplace) %{_sysconfdir}/pam.d/system-config-kdump
%{_datadir}/icons/hicolor/48x48/apps/system-config-kdump.png
%doc ChangeLog COPYING

%changelog
* Tue Sep 11 2007 Dave Lehman <dlehman@redhat.com> 1.0.12-1%{?dist}
- prompt user for a PAE kernel for 32-bit xen with >4G memory (Jarod Wilson)
  Resolves: rhbz#284851

* Wed Aug 29 2007 Dave Lehman <dlehman@redhat.com> 1.0.11-1%{?dist}
- add support for xen (patch from Jarod Wilson)
  Resolves: #243191

* Tue Jan 16 2007 Dave Lehman <dlehman@redhat.com> 1.0.10-1%{?dist}
- handle ia64 bootloader correctly
  Resolves: #220231
- align memory requirements with documented system limits
  Resolves: #228711

* Wed Dec 27 2006 Dave Lehman <dlehman@redhat.com> 1.0.9-3%{?dist}
- only present ext2 and ext3 as filesystem type choices (#220223)

* Wed Dec 27 2006 Dave Lehman <dlehman@redhat.com> 1.0.9-2%{?dist}
- make "Edit Location" button translatable (#216596, again)

* Mon Dec 18 2006 Dave Lehman <dlehman@redhat.com> 1.0.9-1%{?dist}
- more translations
- use file: URIs instead of local: (#218878)

* Tue Dec  5 2006 Dave Lehman <dlehman@redhat.com> 1.0.8-1%{?dist}
- more translations (#216596)

* Wed Nov 29 2006 Dave Lehman <dlehman@redhat.com> 1.0.7-1%{?dist}
- rework memory constraints for increased flexibility (#215990)
- improve consistency WRT freezing/thawing of widgets (#215991)
- update translations (#216596)

* Fri Oct 27 2006 Dave Lehman <dlehman@redhat.com> 1.0.6-1%{?dist}
- add ChangeLog and COPYING as docs

* Thu Oct 26 2006 Dave Lehman <dlehman@redhat.com> 1.0.5-3%{?dist}
- use %%{_sysconfdir} instead of /etc in specfile

* Thu Oct 26 2006 Dave Lehman <dlehman@redhat.com> 1.0.5-2%{?dist}
- remove #!/usr/bin/python from system-config-kdump.py (for rpmlint)

* Thu Oct 26 2006 Dave Lehman <dlehman@redhat.com> 1.0.5-1%{?dist}
- fix install make target to specify modes where needed
- remove unnecessary %%preun
- various specfile fixes to appease rpmlint

* Thu Oct 26 2006 Dave Lehman <dlehman@redhat.com> 1.0.4-2
- fix path to icon in glade file

* Tue Oct 24 2006 Dave Lehman <dlehman@redhat.com> 1.0.4-1
- all location types now in combo box (no text entry for type)
- preserve comment lines from kdump.conf instead of writing config header
- add hicolor icon from Diana Fong

* Thu Oct 19 2006 Dave Lehman <dlehman@redhat.com> 1.0.3-1
- rework UI to only allow one location
- minor spec file cleanup

* Wed Oct 18 2006 Dave Lehman <dlehman@redhat.com> 1.0.2-1
- add support for "core_collector" and "path" handlers
- give choices of "ssh" and "nfs" instead of "net"
- validate results of edit location dialog
- add choice of "none" to default actions
- remove "ifc" support since it's gone from kexec-tools
- update kdump config file header
- fix a couple of strings that weren't getting translated

* Mon Oct 16 2006 Dave Lehman <dlehman@redhat.com> 1.0.1-3
- Fix parsing of "crashkernel=..." string from /proc/cmdline

* Fri Oct 13 2006 Dave Lehman <dlehman@redhat.com> 1.0.1-2
- convert crashkernel values to ints when parsing

* Tue Oct 10 2006 Dave Lehman <dlehman@redhat.com> 1.0.1-1
- Fix bugs in writeDumpConfig and writeBootloaderConfig
- Fix handling of pre-existing "ifc" and "default" directives
- Always leave network interface checkbutton sensitive
- Various minor fixes

* Fri Oct 06 2006 Dave Lehman <dlehman@redhat.com> 1.0.0-1
- Initial build

