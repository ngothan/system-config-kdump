%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}

Summary: A graphical interface for configuring kernel crash dumping
Name: system-config-kdump
Version: 2.0.13
Release: 1%{?dist}
URL: http://fedorahosted.org/system-config-kdump/
License: GPL2+
Group: System Environment/Base
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch
Source0: http://fedorahosted.org/released/system-config-kdump/%{name}-%{version}.tar.bz2
BuildRequires: desktop-file-utils
BuildRequires: intltool, gettext, gnome-doc-utils, docbook-dtds, rarian-compat, scrollkeeper
Requires: pygtk2 >= 2.8.6
Requires: pygtk2-libglade
Requires: usermode >= 1.36
Requires: kexec-tools
Requires: yelp
Requires: python-slip-dbus
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
%{_bindir}/scrollkeeper-update -q || :

%post
touch --no-create %{_datadir}/icons/hicolor
if [ -x /usr/bin/gtk-update-icon-cache ]; then
  gtk-update-icon-cache -q %{_datadir}/icons/hicolor
fi
%{_bindir}/scrollkeeper-update -q || :


%files -f %{name}.lang
%defattr(-,root,root,-)
%{_bindir}/system-config-kdump
%{_datadir}/system-config-kdump
%{_datadir}/applications/*
%{python_sitelib}/*egg*
%{python_sitelib}/sckdump/

%config %{_sysconfdir}/security/console.apps/system-config-kdump
%config %{_sysconfdir}/pam.d/system-config-kdump
%config %{_sysconfdir}/dbus-1/system.d/org.fedoraproject.systemconfig.kdump.mechanism.conf

%{_datadir}/dbus-1/system-services/org.fedoraproject.systemconfig.kdump.mechanism.service
%{_datadir}/polkit-1/actions/org.fedoraproject.systemconfig.kdump.policy
%{_datadir}/icons/hicolor/48x48/apps/system-config-kdump.png

%doc ChangeLog COPYING
%doc %{_datadir}/gnome/help/system-config-kdump
%doc %{_datadir}/omf/system-config-kdump


%changelog
* Tue Jul 23 2013 Martin Milata <mmilata@redhat.com> - 2.0.13-1
- see ChangeLog

* Wed Jul 10 2013 Martin Milata <mmilata@redhat.com> - 2.0.12-1
- see ChangeLog

* Fri Apr 19 2013 Martin Milata <mmilata@redhat.com> - 2.0.11-1
- see ChangeLog

* Wed Nov 28 2012 Roman Rakus <rrakus@redhat.com> - 2.0.10-1
- see ChangeLog

* Tue Sep 11 2012 Roman Rakus <rrakus@redhat.com> - 2.0.9-1
- see ChangeLog

* Wed Aug 22 2012 Roman Rakus <rrakus@redhat.com> - 2.0.8-1
- see ChangeLog

* Wed Jun 13 2012 Roman Rakus <rrakus@redhat.com> - 2.0.7-1
- see ChangeLog

* Mon Oct 24 2011 Roman Rakus <rrakus@redhat.com> - 2.0.6-1
- see ChangeLog

* Thu Sep 30 2010 Roman Rakus <rrakus@redhat.com> - 2.0.5-1
- see ChangeLog

* Fri Mar 26 2010 Roman Rakus <rrakus@redhat.com> - 2.0.4-1
- see ChangeLog

* Tue Feb 02 2010 Roman Rakus <rrakus@redhat.com> 2.0.3-1
- see ChangeLog

* Mon Dec 07 2009 Roman Rakus <rrakus@redhat.com> 2.0.2-1
- Don't be interested in non linux entries in bootloaders conf

* Wed Sep 30 2009 Roman Rakus <rrakus@redhat.com> 2.0.1-1
- updated to polkit1

* Tue May 05 2009 Roman Rakus <rrakus@redhat.com> 2.0.0-1
- Reworked to satisfy system config tools cleanup

* Thu Mar 20 2008 Dave Lehman <dlehman@redhat.com> 1.0.14-1%{?dist}
- require bitmap-fonts
  Resolves: rhbz#433858
- make sure translations containing format specifiers are found
  Resolves: rhbz#314341

* Fri Jan 18 2008 Dave Lehman <dlehman@redhat.com> 1.0.13-1%{?dist}
- handle kdump service start/stop
  Resolves: rhbz#239324
- only suggest reboot if memory reservation altered
  Related: rhbz#239324
- preserve unknown config options
  Resolves: rhbz#253603
- add 'halt' default action
  Related: rhbz#253603

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

