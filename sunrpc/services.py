import re
from pathlib import Path


known_services = {100000: ['portmapper', 'portmap', 'sunrpc', 'rpcbind'],
                  100001: ['rstatd', 'rstat', 'rup', 'perfmeter', 'rstat_svc'],
                  100002: ['rusersd', 'rusers'],
                  100003: ['nfs', 'nfsprog'],
                  100004: ['ypserv', 'ypprog'],
                  100005: ['mountd', 'mount', 'showmount'],
                  100007: ['ypbind'],
                  100008: ['walld', 'rwall', 'shutdown'],
                  100009: ['yppasswdd', 'yppasswd'],
                  100010: ['etherstatd', 'etherstat'],
                  100011: ['rquotad', 'rquotaprog', 'quota', 'rquota'],
                  100012: ['sprayd', 'spray'],
                  100013: ['3270_mapper'],
                  100014: ['rje_mapper'],
                  100015: ['selection_svc', 'selnsvc'],
                  100016: ['database_svc'],
                  100017: ['rexd', 'rex'],
                  100018: ['alis'],
                  100019: ['sched'],
                  100020: ['llockmgr'],
                  100021: ['nlockmgr'],
                  100022: ['x25.inr'],
                  100023: ['statmon'],
                  100024: ['status'],
                  100026: ['bootparam'],
                  100028: ['ypupdated', 'ypupdate'],
                  100029: ['keyserv', 'keyserver'],
                  100033: ['sunlink_mapper'],
                  100037: ['tfsd'],
                  100038: ['nsed'],
                  100039: ['nsemntd'],
                  100043: ['showfhd', 'showfh'],
                  100055: ['ioadmd', 'rpc.ioadmd'],
                  100062: ['NETlicense'],
                  100065: ['sunisamd'],
                  100066: ['debug_svc', 'dbsrv'],
                  100069: ['ypxfrd', 'rpc.ypxfrd'],
                  100071: ['bugtraqd'],
                  100078: ['kerbd'],
                  100101: ['event', 'na.event'],
                  100102: ['logger', 'na.logger'],
                  100104: ['sync', 'na.sync'],
                  100107: ['hostperf', 'na.hostperf'],
                  100109: ['activity', 'na.activity'],
                  100112: ['hostmem', 'na.hostmem'],
                  100113: ['sample', 'na.sample'],
                  100114: ['x25', 'na.x25'],
                  100115: ['ping', 'na.ping'],
                  100116: ['rpcnfs', 'na.rpcnfs'],
                  100117: ['hostif', 'na.hostif'],
                  100118: ['etherif', 'na.etherif'],
                  100120: ['iproutes', 'na.iproutes'],
                  100121: ['layers', 'na.layers'],
                  100122: ['snmp', 'na.snmp', 'snmp-cmc', 'snmp-synoptics', 'snmp-unisys', 'snmp-utk'],
                  100123: ['traffic', 'na.traffic'],
                  100227: ['nfs_acl'],
                  100232: ['sadmind'],
                  100300: ['nisd', 'rpc.nisd'],
                  100303: ['nispasswd', 'rpc.nispasswdd'],
                  100233: ['ufsd', 'ufsd'],
                  100418: ['fedfs_admin'],
                  150001: ['pcnfsd', 'pcnfs'],
                  300019: ['amd', 'amq'],
                  391002: ['sgi_fam', 'fam'],
                  545580417: ['bwnfsd'],
                  600100069: ['fypxfrd', 'freebsd-ypxfrd']}


def update_service_names():
    '''
    Attempt to parse the users local /etc/rpc file if present
    and add the services to the known_services dict (if any).
    This function is called automatically when the module is
    loaded.

    Parameters:
        None

    Returns:
        None
    '''
    if not Path('/etc/rpc').is_file():
        return

    rpc_regex = re.compile(r'([^\s]+)\s+(\d+)(?:\s+(.+))?')

    try:

        with open('/etc/rpc') as f:
            lines = f.readlines()

        for line in lines:

            line = line.split('#', 1)[0].strip()
            match = rpc_regex.match(line)

            if not match:
                continue

            service_names = [match.group(1)]

            if match.group(3) is not None:
                service_names += match.group(3).strip().split()

            known_services[int(match.group(2))] = service_names

    except Exception:
        return


def prog_to_name(prog_id: int, with_alias: bool = True) -> str:
    '''
    Attempts to resolve a prog_id to a human readable service name.
    This is done by performing a lookup on the known_services dict.

    Parameters:
        prog_id     program id to lookup
        with_alias  return the main program name and all its aliases

    Returns:
        Looked up program name (+aliases) or None
    '''
    name_list = known_services.get(prog_id)

    if name_list is None:
        return None

    if len(name_list) == 1 or not with_alias:
        return name_list[0]

    return f'{name_list[0]} ({" ".join(name_list[1:])})'


def name_to_prog(name: str) -> int:
    '''
    Attempts to resolve a prog_id by looking up its name.
    The name can be the main service name or an alias.

    Parameters:
        name        program name to lookup

    Returns:
        Looked up program id
    '''
    for prog_id, service_names in known_services.items():
        if name in service_names:
            return prog_id
