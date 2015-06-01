"""
sentry_taiga.plugin
~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2015 by RochSystems.
:license: MIT, see LICENSE for more details.
"""

from django import forms
from sentry.plugins.bases.issue import IssuePlugin
from django.utils.translation import ugettext_lazy as _

from taiga import TaigaAPI

import sentry_taiga

class TaigaOptionsForm(forms.Form):
    taiga_url = forms.CharField(
        label=_('Taiga URL'),
        widget=forms.TextInput(attrs={'placeholder': 
                                      'e.g. https://taiga.example.com'}),
        help_text=_('Enter the URL for your Taiga server'),
        required=True)

    taiga_username = forms.CharField(
        label=_('Taiga User Name'),
        widget=forms.TextInput(attrs={'placeholder': 'e.g. user@example.com'}),
        help_text=_('Enter your Taiga User name'),
        required=True)

    taiga_password = forms.CharField(
        label=_('Taiga Password'),
        widget=forms.PasswordInput(attrs={'placeholder': 'e.g. your password'}),
        help_text=_('Enter your Taiga User password'),
        required=True)

    taiga_project = forms.CharField(
        label=_('Taiga Project Slug'),
        widget=forms.TextInput(attrs={'placeholder': 'e.g. project-slug'}),
        help_text=_('Enter your project slug.'),
        required=True)

    taiga_labels = forms.CharField(
        label=_('Issue Labels'),
        widget=forms.TextInput(attrs={'placeholder': 'e.g. high, bug'}),
        help_text=_('Enter comma separated labels you '
                    'want to auto assign to issues.'),
        required=False)


class TaigaPlugin(IssuePlugin):
    author = 'RochSystems LLC'
    author_url = 'http://rochsystems.com/'
    version = sentry_taiga.VERSION
    description = "Integrate Taiga issues by linking a repository to a project"
    resource_links = [
        ('Bug Tracker', 'https://github.com/rochsystems/sentry-taiga/issues'),
        ('Source', 'https://github.com/rochsystems/sentry-taiga'),
    ]

    slug = 'taiga'
    title = _('Taiga')
    conf_title = title
    conf_key = 'taiga'
    project_conf_form = TaigaOptionsForm

    def is_configured(self, request, project, **kwargs):
        return bool(self.get_option('taiga_project', project))

    def get_new_issue_title(self, **kwargs):
        return _('Create Taiga Issue')

    def create_issue(self, request, group, form_data, **kwargs):

        url = self.get_option('taiga_url', group.project)
        username = self.get_option('taiga_username', group.project)
        password = self.get_option('taiga_password', group.project)
        project_slug = self.get_option('taiga_project', group.project)
        labels = self.get_option('taiga_labels', group.project)
        
        tg = TaigaAPI(host=url)

        try:
            tg.auth(username=username, password=password)
        except Exception as e:
            raise forms.ValidationError(_('Error Communicating '
                                        'with Taiga: %s') % (e,))

        projects = tg.projects.list()
        
        project = projects.get(slug=project_slug)
        if project is None:
            raise forms.ValidationError(_('No project found in Taiga with slug %s') % 
                                        (project_slug,))

        if not project.is_issues_activated:
            raise forms.ValidationError(_('Project %s has issues disabled.') % 
                                        (project_slug,))

        default_priority = project.default_priority
        default_issue_status = project.default_issue_status
        default_issue_type = project.default_issue_type
        default_severity = project.default_severity

        if default_priority is None:
            raise forms.ValidationError(_('Project %s has no default priority. '
                'Set the default priority in Taiga') % (project.name,))
        if default_issue_status is None:
            raise forms.ValidationError(_('Project %s has no default status. '
                'Set the default issue status in Taiga') % (project.name,))
        if default_issue_type is None:
            raise forms.ValidationError(_('Project %s has no default type. '
                'Set the default issue type in Taiga') % (project.name,))
        if default_severity is None:
            raise forms.ValidationError(_('Project %s has no default severity. '
                'Set the default severity in Taiga') % (project.name,))

        data = {'subject': form_data['title'], 
            'priority': default_priority, 'status': default_issue_status,
            'issue_type': default_issue_type, 'severity': default_severity,
            'description': form_data['description'], 
            'tags': map(lambda x:x.strip(), labels.split(","))}

        issue = project.add_issue(**data)

        return issue.ref


    def get_issue_label(self, group, issue_id, **kwargs):
        return 'TG-%s' % issue_id

    def get_issue_url(self, group, issue_id, **kwargs):
        url = self.get_option('taiga_url', group.project)
        slug = self.get_option('taiga_project', group.project)

        return '%s/project/%s/issue/%s' % (url, slug, issue_id)
