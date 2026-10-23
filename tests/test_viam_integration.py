"""Verify Viam configuration and inspection without contacting hardware."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from viam_integration import client


class ViamIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_configuration_fails_before_connecting(self):
        with patch.dict("os.environ", {}, clear=True), patch.object(
            client.RobotClient, "at_address", new_callable=AsyncMock
        ) as dial:
            with self.assertRaisesRegex(ValueError, "Missing required environment variables"):
                await client.connect()
            dial.assert_not_awaited()

    async def test_machine_uuid_is_rejected_as_address(self):
        config = {
            "VIAM_MACHINE_ADDRESS": "00000000-0000-0000-0000-000000000000",
            "VIAM_API_KEY": "test-only-placeholder",
            "VIAM_API_KEY_ID": "test-only-placeholder",
        }
        with patch.dict("os.environ", config, clear=True):
            with self.assertRaisesRegex(ValueError, "ID, not a hostname"):
                await client.connect()

    async def test_list_only_does_not_read_hardware(self):
        machine = AsyncMock()
        machine.__aenter__.return_value = machine
        machine.resource_names = [
            SimpleNamespace(namespace="rdk", type="component", subtype="arm", name="arm")
        ]
        with patch.object(client, "connect", AsyncMock(return_value=machine)), patch.object(
            client.Arm, "from_robot"
        ) as arm:
            self.assertEqual(await client.inspect_machine(list_only=True), 0)
            arm.assert_not_called()
        machine.__aexit__.assert_awaited_once()

    async def test_failed_read_continues_and_closes_connection(self):
        machine = AsyncMock()
        machine.__aenter__.return_value = machine
        machine.resource_names = [
            SimpleNamespace(namespace="rdk", type="component", subtype=subtype, name=name)
            for subtype, name in [("arm", "arm"), ("gripper", "gripper")]
        ]
        arm = AsyncMock()
        arm.get_joint_positions.side_effect = RuntimeError("test read failure")
        gripper = AsyncMock()
        gripper.is_moving.return_value = False
        with patch.object(client, "connect", AsyncMock(return_value=machine)), patch.object(
            client.Arm, "from_robot", return_value=arm
        ), patch.object(client.Gripper, "from_robot", return_value=gripper):
            self.assertEqual(await client.inspect_machine(), 1)
            gripper.is_moving.assert_awaited_once()
        machine.__aexit__.assert_awaited_once()
