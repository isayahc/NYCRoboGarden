"""Connect to Viam and inspect resources without moving hardware."""

import asyncio
import os
import sys
from uuid import UUID

from viam.robot.client import RobotClient
from viam.components.arm import Arm
from viam.components.gripper import Gripper

async def connect():
    required = ("VIAM_MACHINE_ADDRESS", "VIAM_API_KEY", "VIAM_API_KEY_ID")
    config = {name: os.getenv(name, "").strip() for name in required}
    missing = [name for name, value in config.items() if not value]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    address = config["VIAM_MACHINE_ADDRESS"]
    try:
        UUID(address)
    except ValueError:
        pass
    else:
        raise ValueError(
            "VIAM_MACHINE_ADDRESS is an ID, not a hostname. Copy the machine "
            "address (ending in .viam.cloud) from its CONNECT tab into .env."
        )

    opts = RobotClient.Options.with_api_key(
        api_key=config["VIAM_API_KEY"],
        api_key_id=config["VIAM_API_KEY_ID"]
    )

    return await asyncio.wait_for(RobotClient.at_address(address, opts), timeout=30)

async def inspect_machine(list_only=False):
    failures = 0
    async with await connect() as machine:
        print("Connected to Viam. Resources:")
        resources = sorted(machine.resource_names, key=lambda resource: resource.name)
        for resource in resources:
            print(f"  {resource.namespace}:{resource.type}:{resource.subtype}/{resource.name}")
        if list_only:
            return 0

        for resource in resources:
            if resource.namespace != "rdk" or resource.type != "component":
                continue
            try:
                if resource.subtype == "arm":
                    arm = Arm.from_robot(machine, resource.name)
                    result = await arm.get_joint_positions(timeout=10)
                    print(f"{resource.name} joint positions (degrees): {list(result.values)}")
                elif resource.subtype == "gripper":
                    gripper = Gripper.from_robot(machine, resource.name)
                    result = await gripper.is_moving(timeout=10)
                    print(f"{resource.name} is moving: {result}")
            except Exception as exc:
                failures += 1
                print(f"{resource.name}: hardware read failed: {exc}", file=sys.stderr)
        if failures:
            print(
                "Viam connectivity works, but hardware reads failed. Check the "
                "affected arm's power, USB/serial connection and component configuration.",
                file=sys.stderr,
            )
    return 1 if failures else 0
