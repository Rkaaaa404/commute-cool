"""HDFS WebHDFS Client - Write ingestion data directly to HDFS Bronze layer.
"""
from __future__ import annotations

import os
import requests


def write_to_hdfs(hdfs_path: str, data_str: str) -> bool:
    """Write string content directly to HDFS via WebHDFS.
    
    If successful, returns True. Otherwise, returns False.
    """
    # HDFS_NAMENODE is hdfs://namenode:9000 by default in docker env
    hdfs_namenode = os.getenv("HDFS_NAMENODE", "hdfs://namenode:9000")
    
    # Extract host name from hdfs url
    namenode_host = hdfs_namenode.replace("hdfs://", "").split(":")[0]
    
    # WebHDFS is exposed on port 9870 in hadoop namenode by default
    webhdfs_url = f"http://{namenode_host}:9870/webhdfs/v1{hdfs_path}?op=CREATE&overwrite=true&user.name=root"
    
    try:
        # Step 1: Initialize CREATE request without following redirect
        # Namenode will check permissions and direct us to datanode
        print(f"  [HDFS] Initiating upload to {hdfs_path} using WebHDFS...")
        response = requests.put(webhdfs_url, allow_redirects=False, timeout=10)
        
        if response.status_code == 307:
            # Step 2: Extract redirection URL (Datanode address)
            datanode_url = response.headers.get("Location")
            if not datanode_url:
                print("  [HDFS] Error: Redirect location header not found")
                return False
            
            # Step 3: Put data directly to Datanode
            print(f"  [HDFS] Uploading raw payload directly to Datanode...")
            headers = {"Content-Type": "application/octet-stream"}
            r_upload = requests.put(
                datanode_url, 
                data=data_str.encode("utf-8"), 
                headers=headers, 
                timeout=30
            )
            
            if r_upload.status_code == 201:
                print(f"  [HDFS] ✓ Successfully uploaded to HDFS: {hdfs_path}")
                return True
            else:
                print(f"  [HDFS] ✗ Datanode write failed: {r_upload.status_code} - {r_upload.text}")
                return False
        else:
            print(f"  [HDFS] ✗ Namenode handshake failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"  [HDFS] ✗ Connection to HDFS failed: {e}")
        return False
