#!/usr/bin/python

# (c) 2016, Andre Lehmann <andre.lehmann@posteo.de>
#
# This file is part of DockerContainerConfigurator,
#
# DockerContainerConfigurator is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# DockerContainerConfigurator is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with DockerContainerConfigurator.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

DOCUMENTATION = '''
---
module: docker_container_configurator
short_description: creates configurations to compose docker container
description:
author: "Andre Lehmann"
'''

import jinja2
import re

def jinja2_filter_required(value, error_massage=u''):
    """ Throws an 'UndefinedError' with an custom error massage, when value is undefined

    Args:
        value: Some value
        error_massage (str): Massage to be displayed, when an exceptin is thrown

    Returns:
        value.  Unchanged value

    """

    if type(value) is jinja2.Undefined:
        raise jinja2.UndefinedError(error_massage)

    return value

def _merge_dicts(first, second):
    """ Recursivly merges two dicts

    When keys exist in both the value of 'second' is used.

    Args:
        first (dict): First dict
        second (dict): Second dict

    Returns:
        dict.  Merged dict containing values of first and second

    """
    # when one of the dicts is empty, than just return the other one
    if first is None:
        if second is None:
            return dict()
        else:
            return second
    if second is None:
        if first is None:
            return dict()
        else:
            return first

    merged = {}
    for k in set(first.keys()).union(second.keys()):
        if k in first and k in second:
            if isinstance(first[k], dict) and isinstance(second[k], dict):
                # merge dicts
                merged[k] = _merge_dicts(first[k], second[k])
            elif isinstance(first[k], list) and isinstance(second[k], list):
                # merge lists
                merged[k] = first[k] + second[k]
            else:
                # replace first[k] with second[k]
                merged[k] = second[k]
        elif k in first:
            merged[k] = first[k]
        else:
            merged[k] = second[k]

    return merged

def _remove_omit_placeholder(string):
    """ Removes the omit placeholder of ansible with an empty string.

    Args:
        string (str): Input string possibly containing omit placeholders.

    Returns:
        str.  Input string but with replaced placeholders.

    """
    regex_pattern = r'__omit_place_holder__[0-9a-f]{40}'
    return re.sub(regex_pattern, '', string)

class ContainerConfiguration:
    """ Represents a rendered container configuration.

    Args:
        name (str): Name of the configuration.
        template (ContainerTemplate): Template used as a template for the configuration.
        config (dict): Variables to render the template using jinja2.

    """
    _defintion_name = ""
    _name = ""
    _configuration = dict()

    def __init__(self, name, template, config):
        self._name = name
        self._defintion_name = template.get_name()

        try:
            self._configuration = self._create_rendered_configuration(template, config)
        except jinja2.exceptions.TemplateError as e:
            raise jinja2.exceptions.TemplateError("Error while configuring '{0}' with container template '{1}': {2}".format(self._name, self._defintion_name, e.message))

        if not self._configuration.has_key('image') or self._configuration['image'] is None:
            raise KeyError("Invalid container configuration '{0}', because the template '{1}' does not contain an image tag".format(self._name, self._defintion_name))

    def get_template_name(self):
        """ Gets the name of the used template.

        Returns:
            str.  The template name.

        """
        return self._defintion_name

    def get_name(self):
        """ Gets the name of the configuration.

        Returns:
            str.  The name of the configuration.

        """
        return self._name

    def get_configuration(self):
        """ Gets configuration as a dict.

        Returns:
            dict.  The configuration as a dict.

        """
        return self._configuration

    def _render_value(self, value, context):
        """ Renders a value with jinja2.

        Args:
            value (dict, list, bool, float, str): Value to be rendered with jinja2.
            context (dict): Variables used to render the value.

        Returns:
            None, float, bool, str, list, dict.  Rendered value.

        """
        jinja_env = jinja2.Environment(undefined=jinja2.Undefined)
        jinja_env.filters['required'] = jinja2_filter_required
        if isinstance(value, dict):
            new_value = dict()
            for key in value.iterkeys():
                result = self._render_value(value[key], context)
                if result is not None:
                    new_value[key] = result
            return new_value if len(new_value) > 0 else None
        elif isinstance(value, list):
            new_value = list()
            for item in value:
                result = self._render_value(item, context)
                if result is not None:
                    new_value.append(result)
            return new_value if len(new_value) > 0 else None
        elif isinstance(value, str):
            value = _remove_omit_placeholder(value)
            result = jinja_env.from_string(value) \
                .render(context).encode('utf-8')
            return result if len(result) > 0 else None
        else:
            return value

    def _create_rendered_configuration(self, template, config):
        """ Creates a rendered configuration based on a template and config variables.

        Args:
            template (dict): Template for the configuration.
            config (dict): Variables to fill the template.

        Returns:
            dict.  Rendered configuration as a dict.

        """
        configured_container = {}
        cnt_template = template.get_template()
        cnt_template = _merge_dicts(cnt_template, self._get_docker_parameter_from_config(config))

        config['CONTAINER_CONFIG_NAME'] = self._name
        for key in cnt_template.iterkeys():
            result = self._render_value(cnt_template[key], config)
            if result is not None:
                configured_container[key] = result

        return configured_container

    def _get_docker_parameter_from_config(self, cnt_config):
        """ Creates a dict with only official parameter from the container config.

        Args:
            cnt_config (dict): Container configuration.

        Returns:
            dict.  Official parameter from the container config.

        """
        parameter = [
            'api_version',
            'auto_remove',
            'blkio_weight',
            'cacert_path',
            'capabilities',
            'cert_path',
            'cleanup',
            'command',
            'cpu_period',
            'cpu_quota',
            'cpu_shares',
            'cpuset_cpus',
            'cpuset_mems',
            'detach',
            'devices',
            'dns_search_domains',
            'dns_servers',
            'docker_host',
            'entrypoint',
            'env',
            'env_file',
            'etc_hosts',
            'exposed_ports',
            'force_kill',
            'groups',
            'hostname',
            'ignore_image',
            'image',
            'interactive',
            'ipc_mode',
            'keep_volumes',
            'kernel_memory',
            'key_path',
            'kill_signal',
            'labels',
            'links',
            'log_driver',
            'log_options',
            'mac_address',
            'memory',
            'memory_reservation',
            'memory_swap',
            'memory_swappiness',
            'name',
            'network_mode',
            'networks',
            'oom_killer',
            'oom_score_adj',
            'paused',
            'pid_mode',
            'privileged',
            'published_ports',
            'pull',
            'purge_networks',
            'read_only',
            'recreate',
            'restart',
            'restart_policy',
            'restart_retries',
            'security_opts',
            'shm_size',
            'ssl_version',
            'state',
            'stop_signal',
            'stop_timeout',
            'sysctls',
            'timeout',
            'tls',
            'tls_hostname',
            'tls_verify',
            'tmpfs',
            'trust_image_content',
            'tty',
            'ulimits',
            'user',
            'uts',
            'volume_driver',
            'volumes',
            'volumes_from',
            'working_dir'
        ]
        result = dict()
        for param in parameter:
            for key in cnt_config.iterkeys():
                if key == param:
                    result[key] = cnt_config[key]
        return result

    def get_linked_container(self):
        """ Gets the links of this configuration.

        Returns:
            list, None.  All links defined for this configuration. When 'links' is not defined 'None' will be returned.

        """
        if self._configuration.has_key('links'):
            links = self._configuration['links']
            if isinstance(links, list):
                return links
            elif isinstance(links, str):
                ret = [links]
                return ret

        return None


class ContainerTemplate:
    """ Represents a generic container template.

    Args:
        name (str): Name of the template.
        partial_templates (dict): Partial templates before the dependencies have been solved.

    """
    _name = ""
    _template = dict()

    def __init__(self, name, partial_templates):
        self._name = name
        self._template = self._get_parent_template(name, partial_templates, 0)

    def get_name(self):
        """ Gets the name of the template.

        Returns:
            str.  The name of the template.

        """
        return self._name

    def get_template(self):
        """ Gets the template as a dict.

        Returns:
            dict.  The template as a dict.

        """
        return self._template

    def _get_parent_template(self, parent_name, partial_templates, recursion_level):
        """ Gets the template of the parent partial template and merges it.

        Args:
            parent_name (dict): Name of the parent template.
            partial_templates (dict): Partial templates.
            recursion_level (int): Depth of the recursion.

        Returns:
            dict.  Template as a dict.

        """
        # throw exception when a template is missing
        if not partial_templates.has_key(parent_name):
            raise KeyError("Container template does not contain '{0}'".format(parent_name))

        partial_template = partial_templates[parent_name]
        cnt_template = partial_template

        if recursion_level > 20:
            raise RuntimeError("Maximum recursion depth exceeded. Check your code for a cyclic based_on statement")
        recursion_level +=1

        # check this partial template is based on a parent template
        if partial_template.has_key('based_on'):
            if partial_template['based_on'] is None:
                pass
            elif isinstance(partial_template['based_on'], list):
                for parent in partial_template['based_on']:
                    if isinstance(parent, str):
                        parent = _remove_omit_placeholder(parent)
                        if parent != "":
                            cnt_template = _merge_dicts(self._get_parent_template(parent, partial_templates, recursion_level), cnt_template)
            elif isinstance(partial_template['based_on'], str):
                parent = _remove_omit_placeholder(partial_template['based_on'])
                if parent != "":
                    cnt_template = _merge_dicts(self._get_parent_template(parent, partial_templates, recursion_level), cnt_template)

        return cnt_template


def create_templates(container_partial_templates):
    """ Creates container templates based on the partial templates.

    Args:
        container_partial_templates (dict): Partial templates as a base for the container templates.

    Returns:
        list.  List containing all container templates.

    """
    container_templates = list()
    for key in container_partial_templates.iterkeys():
        container_templates.append(ContainerTemplate(key, container_partial_templates))

    return container_templates

def create_configurations(templates, config):
    """ Creates container configurations based on container templates and config variables.

    Args:
        templates (list): Container templates as a generic base for the configurations.
        config (dict): Variables to render the templates using jinja2.

    Returns:
        list.  List containing all container configurations.

    """
    container_configurations = list()
    for key in config.iterkeys():
        cnt_config = config[key]
        if not cnt_config.has_key('template'):
            raise KeyError("Container configuration '{0}' does not contain 'template' declaration".format(cnt_config))

        cnt_template = None
        for template in templates:
            if template.get_name() == cnt_config['template']:
                cnt_template = template
                break
        if cnt_template is None:
            raise KeyError("Container template does not contain '{0}'".format(cnt_config['template']))

        container_configurations.append(ContainerConfiguration(key, cnt_template, cnt_config))

    return container_configurations

def get_link_order(configuration, container_configurations, recursion_level):
    """ Creates a list with the right linking order of a configuration.

    Args:
        configuration (ContainerConfiguration): Configuration to find the link order for.
        container_configurations (list): All configurations.
        recursion_level (int): Depth of the recursion.

    Returns:
        list.  List containing the link order for the given configuration.

    """
    if recursion_level > 20:
        raise RuntimeError("Maximum recursion depth exceeded. Check your template for cyclic container linking: {0}".format(type(configuration.get_linked_container()[0])))
    recursion_level +=1

    cnt_link_order = list()
    cnt_link_order.append(configuration)
    cnt_links = configuration.get_linked_container()
    if cnt_links is not None:
        for cnt_link in cnt_links:
            # strip link name to contain only the container name (e.g. some_mysql:mysql --> somemysql)
            tmp = re.match(r'.*?(?=\:)', cnt_link, flags=0)
            if tmp:
                cnt_link = tmp.group()
            for cnt_config in container_configurations:
                config_dict = cnt_config.get_configuration()
                if config_dict.has_key('name') and config_dict['name'] == cnt_link:
                    cnt_link_order = get_link_order(cnt_config, container_configurations, recursion_level) + cnt_link_order
                    break

    return cnt_link_order


def create_run_order(container_configurations, run_order):
    """ Creates the run order for the given configurations considering 'run_order' and the link order.

    Args:
        container_configurations (list): All container configurations.
        run_order (list): Predefined run order used as a priority list.

    Returns:
        list.  List with all configurations in the right run and link order.

    """
    cnt_config_in_order = list()
    if isinstance(run_order, list):
        for cnt_template_name in run_order:
            for cnt_config in container_configurations:
                if cnt_config.get_template_name() == cnt_template_name:
                    link_order = get_link_order(cnt_config, container_configurations, 0)
                    for l in link_order:
                        if l not in cnt_config_in_order:
                            cnt_config_in_order.append(l)

    for cnt_config in container_configurations:
        if cnt_config not in cnt_config_in_order:
            link_order = get_link_order(cnt_config, container_configurations, 0)
            for l in link_order:
                if l not in cnt_config_in_order:
                    cnt_config_in_order.append(l)

    return cnt_config_in_order

def main():
    module = AnsibleModule(
        argument_spec = dict(
            templates = dict(required=True, default=None, type='dict'),
            config = dict(required=True, default=None, type='dict'),
            run_order   = dict(required=False, default=None, type='list')
        )
    )

    try:
        container_templates = create_templates(module.params.get('templates'))
        container_configurations = create_configurations(container_templates, module.params.get('config'))
        container_configurations_in_run_order = create_run_order(container_configurations, module.params.get('run_order'))

        list_of_configurations = list()
        for c in container_configurations_in_run_order:
            list_of_configurations.append(c.get_configuration())

        module.exit_json(changed=False, ansible_facts={"docker_container_configurations": list_of_configurations})
    except Exception as e:
        module.fail_json(changed=False, msg=repr(e))

# import module snippets
from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
