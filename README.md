# Ansible - Docker Container Configurator

Ansible role for creating docker container compositions. It let's you easily manage extensive container compositions with a lot of containers and detailed startup parameters. Based on reusable templates the container configuration is created and then used with the *[docker_container](http://docs.ansible.com/ansible/docker_container_module.html)* module to manage the container.

## Requirements

This roles requires Ansible 2.1.0 with the new introduced *docker_container* module.

## Usage

Example playbook:

```yaml
- hosts: localhost
  vars:
    templates: # the templates
      webserver:
        ...
      gitservice:
        ...
    run_order: # optional custom run order
      - gitservice
      - webserver
  roles:
    - role: docker_container_configurator
      config: # configuration (composition) of containers
        webapp1:
          template: webserver
        webapp2:
          template: webserver
        webapp3:
          template: gitservice
```

### Role Variables

There are three variables to be passed into the role:

Variable  | Purpose  | Type |  Mandatory
--------- | -------- | ---- | ----------
templates | Defines all the templates that can be used to create a container configurations. | Dict | yes
config    | The custom configuration using the predefined templates. | Dict | yes
run_order | Specifies a custom run order in which the container shall be managed. The proper container link order of the any container is preserved. | List | no

### Templates


Before a container configuration can be created a template must be defined. It consists mostly of the official *docker_container* options. A comprehensive list of all those options can be found [here](http://docs.ansible.com/ansible/docker_container_module.html).

#### Basic Structure

The basic structure of the dict is following:

```yaml
templates:
  webserver: # first template
    # all options are defined here
    name: "{% raw %}{{ CONTAINER_CONFIG_NAME }}{% endraw %}"
    image: nginx
  gitservice: # second template
    name: "{% raw %}{{ CONTAINER_CONFIG_NAME }}{% endraw %}"
    image: gogs
    env:
      SOMEVAR: "{% raw %}{{ SOMEVAR }}{% endraw %}"
```

In this example two templates are defined, `webserver` and `gitservice`. These can be used later on. To pass variables into the templates those must be [escaped](http://jinja.pocoo.org/docs/dev/templates/#escaping). To escape *jinja2* code simply put it into a `{% raw %}...{% endraw %}` block. Escaped variables will be evaluated every time a template is used.

#### Inheritance

Templates can inherit from each other. This way a template only has to specify any unique options and then inherit the other options from a base template. There is no inheritance limit, so you can create arbitrary inheritance trees. The true power of this role (+library) lies within the merging of options. A template will overwrite *bool*, *float* and *string* options specified in a base template and merge *dict* and *list* options. E.g. you can specify common environmental variables in a base template and add more in child templates. Envs that are respecified in the child template would replace the ones in the base template.
To inherit a template simply add `based_on` keyword in the template definition. Here is an example:

```yaml
templates:
  base:
    detach: yes
    state: started
  webserver:
    based_on: base # inherit from base template
    name: "{% raw %}{{ CONTAINER_NAME }}{% endraw %}"
    image: nginx
    env:
      DOMAINNAME: "{% raw %}{{ DOMAINNAME }}{% endraw %}"
  phpmyadmin:
    based_on: webserver
    name: "{% raw %}{{ CONTAINER_NAME }}{% endraw %}"
    image: phpmyadmin-nginx
    env:
      SOMEVAR: "{% raw %}{{ SOMEVAR }}{% endraw %}"
```

When the template `phpmyadmin` is used a configuration as follows could be created:

```yaml
phpmyadmin:
  based_on: webserver
  name: some_container_name
  image: phpmyadmin-nginx
  detach: yes
  state: started
  env:
    DOMAINNAME: "domain.tld"
    SOMEVAR: "is it so hard to live in peace?"
```

### Configuration

Once the template are defined, these can be used in a configuration. Look at the configuration as the instances of a class. These instances can have they own set of variables. These variables can be used for rendering the templates and even replace option by explicitly defining those in the configuration:

Look at following example:

```yaml
  config:
    webapp1: # name of configuration can be used as a variable (CONTAINER_CONFIG_NAME)
      template: webserver
      DOMAINNAME: www.domain.tld # will be used to fill out "{% raw %}{{ DOMAINNAME }}{% endraw %}" on runtime
    webapp2:
      template: webserver
      DOMAINNAME: support.domain.tld
      state: absent # will overwrite option from the template
    phpmyadmin:
      template: phpmyadmin
      DOMAINNAME: mysql.domain.tld
      SOMEVAR: "Confy McConfyface"
```

This configuration will manage 3 containers. Two of them will be started and one will be removed. The container configurations `webapp1` and `webapp2` are using the template `webserver` and the config `phpmyadmin` is using the eponymous template `phpmyadmin`. All of them define some variables like `DOMAINNAME` which will be used int the templates (`{% raw %}{{ DOMAINNAME }}{% endraw %}`). `webapp2` overwrites the *state* option of its template.

### Run Order

The run ordner is optional. It can be used to customize the order in which the containers are managed. Don't worry about the linking order. The library will take care of the proper linking order for you even though specified a *run_order*. The run order is simply a list with the names of the templates in the preferred order to be managed. Example:

```yaml
run_order:
  - phpmyadmin
  - webserver
```

If this run order is in place then all configuration which are using the `phpmyadmin` template will be manged before those using `webserver`.

### Examples

Detailed examples can be found in the [examples dir](examples/)

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
