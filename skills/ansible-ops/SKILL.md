---
name: ansible-ops
description: Ansible playbook, inventory, and task conventions. Use when creating, editing, or reviewing Ansible playbooks, inventories, roles, or tasks.
---
# Ansible Operations

## Playbook Conventions
- Always set `gather_facts: false` unless the playbook specifically needs system facts (e.g., `ansible_date_time`)
- Use `throttle: N` on plays targeting large inventories to limit concurrent execution
- Use `become: yes` only for tasks requiring root (apt, systemd, sysctl, file ops in system dirs)
- Access per-host variables via `hostvars[inventory_hostname].var_name`
- Use `block` / `when` for conditional task groups
- Use `register` + `debug` for diagnostic output
- Add YAML schema comment at file top when generating inventory files

## Safety Rules
- Always include `--limit` in examples and when running against production inventories
- Prefer `--check` (dry-run) mode first for destructive operations
- Create backups with `ansible_date_time.epoch` timestamps before modifying config files
- Never hardcode secrets (passwords, tokens, keys, DSNs) in playbook files — use `-e` extra vars or inventory vars
- Provide dry-run playbook variants for risky operations

## Module Preferences
- **Docker**: `docker_container`, `docker_login`, `docker_image` — prefer these over `shell`/`command` with docker CLI
- **Config files**: `template` for Jinja2 templates, `lineinfile` for single-line edits
- **Packages**: `apt` module (not shell apt-get)
- **Services**: `systemd` or `service` module
- **File discovery**: `find` and `stat` modules
- **Remote file content**: `slurp` module (returns base64, decode with `b64decode` filter)
- **Config changes**: prefer `lineinfile`/`template` over raw `shell` commands

## Inventory Patterns
- YAML format with group hierarchy (parent groups using `children:` key)
- Variable inheritance: global vars in a shared inventory file, per-host vars under `hosts:`
- Environment separation: test, staging, prod as child groups under a parent group
- Host variables: `ansible_host`, `ansible_user`, `ansible_port`, `ansible_python_interpreter`

## Task Patterns
```yaml
# Typical task structure
- name: Descriptive task name
  module_name:
    param: value
  become: yes          # only if needed
  register: result     # when output is needed
  when: condition      # conditional execution
  failed_when: ...     # custom failure conditions

# Docker container pattern
- name: Deploy container
  docker_container:
    name: my-container
    image: "{{ registry }}/image:{{ version }}"
    state: started
    restart_policy: unless-stopped
    networks:
      - name: my-network
        ipv4_address: "172.18.0.10"
    volumes:
      - /host/path:/container/path
    env:
      VAR_NAME: "{{ var_value }}"

# Backup before destructive operation
- name: Create backup
  copy:
    src: /path/to/config.yml
    dest: "/path/to/config.yml.backup.{{ ansible_date_time.epoch }}"
    remote_src: yes
  become: yes

# Read remote file content
- name: Read config
  slurp:
    src: /path/to/file
  register: file_content

- name: Parse content
  set_fact:
    parsed: "{{ file_content.content | b64decode }}"
```

## Anti-Patterns to Avoid
- Don't use `shell: docker run ...` when `docker_container` module works
- Don't use `shell: apt-get install` when `apt` module works
- Don't set `gather_facts: true` by default — only enable when facts are used
- Don't hardcode IPs, passwords, or tokens in playbook files
- Don't run against all hosts without `--limit` on production inventories
