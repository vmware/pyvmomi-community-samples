#!/usr/bin/env python3
"""
Retrieve VM initial swap reservation from vCenter cluster ESXi hosts.

This script connects to a vCenter server, identifies a specified cluster,
and retrieves the initialSwapReservation property for VMs on all or a specific
ESXi host in that cluster.

Requirements:
    pip install pyvmomi

Usage:
    # Query all hosts in a cluster
    python get_vm_initial_swap_reservation.py -s <vCenter> -u <user> -p <password> \\
        --cluster-name <cluster_name>

    # Query a specific host in a cluster
    python get_vm_initial_swap_reservation.py -s <vCenter> -u <user> -p <password> \\
        --cluster-name <cluster_name> --esx-ip <host_ip>

    # Export results to CSV
    python get_vm_initial_swap_reservation.py -s <vCenter> -u <user> -p <password> \\
        --cluster-name <cluster_name> --csv report.csv

    # Disable SSL verification
    python get_vm_initial_swap_reservation.py -s <vCenter> -u <user> -p <password> \\
        --cluster-name <cluster_name> -nossl
"""

import csv
import logging
from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
from tools import cli, service_instance

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def get_cluster_by_name(si, cluster_name):
    """Retrieve a cluster by name from vCenter."""
    try:
        content = si.RetrieveContent()
        container = content.rootFolder
        view_type = [vim.ClusterComputeResource]
        recursive = True
        container_view = content.viewManager.CreateContainerView(container, view_type, recursive)

        try:
            for cluster in container_view.view:
                if cluster.name == cluster_name:
                    return cluster
        finally:
            container_view.Destroy()

        logging.error(f"Cluster '{cluster_name}' not found.")
        return None

    except Exception as e:
        logging.error(f"Error retrieving cluster '{cluster_name}': {e}")
        return None


def get_vms_swap_reservation_from_cluster(cluster, host_filter=None):
    """
    Retrieve VM initial swap reservation for all VMs in all hosts in a cluster.
    If host_filter is specified, only query that specific host.
    Returns list of dicts with VM and swap reservation info.
    """
    vm_data = []

    try:
        # Iterate through all hosts in the cluster
        hosts_to_query = cluster.host
        if host_filter:
            hosts_to_query = [h for h in cluster.host if h.name == host_filter]
            if not hosts_to_query:
                logging.error(f"Host '{host_filter}' not found in cluster.")
                return None

        for host in hosts_to_query:
            host_name = host.name
            print(f"\n{'='*95}")
            print(f"ESXi Host: {host_name}")
            print('='*95)

            print(f"{'VM Name':<40} | {'Swap Reservation (Bytes)':<25} | {'Swap Reservation (MB)':<20}")
            print("-" * 95)

            host_total_swap_bytes = 0
            host_vms_with_swap = 0
            host_vms_without_swap = 0

            # Iterate through all VMs on the host
            for vm in host.vm:
                if not vm.config:
                    continue

                vm_name = vm.name
                initial_overhead = getattr(vm.config, 'initialOverhead', None)

                swap_bytes = None
                swap_mb = None

                if initial_overhead and hasattr(initial_overhead, 'initialSwapReservation'):
                    swap_bytes = initial_overhead.initialSwapReservation
                    if swap_bytes is not None:
                        swap_mb = round(swap_bytes / (1024 * 1024), 2)
                        host_total_swap_bytes += swap_bytes
                        host_vms_with_swap += 1
                        print(f"{vm_name:<40} | {swap_bytes:<25} | {swap_mb:<20} MB")
                    else:
                        host_vms_without_swap += 1
                        print(f"{vm_name:<40} | {'None':<25} | {'None':<20}")
                else:
                    host_vms_without_swap += 1
                    print(f"{vm_name:<40} | {'Not Set':<25} | {'Not Set':<20}")

                vm_data.append({
                    'host_name': host_name,
                    'vm_name': vm_name,
                    'swap_bytes': swap_bytes,
                    'swap_mb': swap_mb,
                })

            # Print host summary
            print("-" * 95)
            print(f"Summary for {host_name}:")
            print(f"  Total VMs: {host_vms_with_swap + host_vms_without_swap}")
            print(f"  VMs with swap reservation set: {host_vms_with_swap}")
            print(f"  VMs without swap reservation: {host_vms_without_swap}")
            print(f"  Total swap reservation: {host_total_swap_bytes:,} bytes ({round(host_total_swap_bytes / (1024**3), 2)} GB)")

    except Exception as e:
        logging.error(f"Error retrieving VM data from cluster: {e}")
        return None

    return vm_data


def main():
    parser = cli.Parser()
    parser.add_custom_argument('--cluster-name', required=True,
                              help='Name of the cluster to query')
    parser.add_optional_arguments(cli.Argument.ESX_IP)
    parser.add_custom_argument('--csv', required=False,
                              help='Export results to CSV file')
    args = parser.get_args()

    try:
        # Connect to vCenter
        logging.info(f"Connecting to vCenter at {args.host}...")
        si = service_instance.connect(args)

        # Get the cluster
        logging.info(f"Retrieving cluster '{args.cluster_name}'...")
        cluster = get_cluster_by_name(si, args.cluster_name)

        if not cluster:
            logging.error(f"Cluster '{args.cluster_name}' not found. Exiting.")
            Disconnect(si)
            return 1

        # Get VM swap reservation data
        if args.esx_ip:
            logging.info(f"Querying VMs on host '{args.esx_ip}' in cluster '{args.cluster_name}'...")
        else:
            logging.info(f"Querying VMs in cluster '{args.cluster_name}'...")
        vm_data = get_vms_swap_reservation_from_cluster(cluster, args.esx_ip)

        if vm_data is None:
            Disconnect(si)
            return 1

        # Print overall summary
        if vm_data:
            total_swap_bytes = sum(vm['swap_bytes'] for vm in vm_data if vm['swap_bytes'] is not None)
            total_vms = len(vm_data)
            vms_with_swap = sum(1 for vm in vm_data if vm['swap_bytes'] is not None)

            print(f"\n{'='*95}")
            print(f"Overall Summary for Cluster '{args.cluster_name}':")
            print('='*95)
            print(f"  Total VMs: {total_vms}")
            print(f"  VMs with swap reservation set: {vms_with_swap}")
            print(f"  VMs without swap reservation: {total_vms - vms_with_swap}")
            print(f"  Total swap reservation: {total_swap_bytes:,} bytes ({round(total_swap_bytes / (1024**3), 2)} GB)")

            # Export to CSV if requested
            if args.csv:
                with open(args.csv, 'w', newline='') as csvfile:
                    fieldnames = ['host_name', 'vm_name', 'swap_bytes', 'swap_mb']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(vm_data)
                logging.info(f"Data exported to: {args.csv}")

        Disconnect(si)
        return 0

    except Exception as e:
        logging.error(f"Error: {e}")
        return 1


if __name__ == '__main__':
    exit(main())
