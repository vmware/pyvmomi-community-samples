from unittest import TestCase
from mock import Mock

from samples.interactive_wrapper import VM, ESX, VVC, get_all_vms_in_folder

class VMTests(TestCase):

    def setUp(self):
        self.raw_vm = Mock()
        self.wrapped_vm = VM(self.raw_vm)

    def test_should_passthrough_unwrapped_attributes(self):
        self.assertEqual(self.wrapped_vm.anything, self.raw_vm.anything)

    def test_should_return_interface_when_one_matches(self):
        foo_mock = lambda: None
        foo_mock.name = "foo"
        bar_mock = lambda: None
        bar_mock.name = "bar"
        self.raw_vm.network = [foo_mock, bar_mock]

        actual_matching_interface = self.wrapped_vm.get_first_network_interface_matching(lambda n: n.name == "bar")

        self.assertEqual(actual_matching_interface, bar_mock)

    def test_should_return_first_interface_when_several_match(self):
        aha_mock = lambda: None
        aha_mock.name = "aha"
        foo_mock_1 = lambda: None
        foo_mock_1.name = "foo"
        bar_mock = lambda: None
        bar_mock.name = "bar"
        foo_mock_2 = lambda: None
        foo_mock_2.name = "foo"
        self.raw_vm.network = [aha_mock, foo_mock_1, bar_mock, foo_mock_2]

        actual_matching_interface = self.wrapped_vm.get_first_network_interface_matching(lambda n: n.name == "foo")

        self.assertEqual(actual_matching_interface, foo_mock_1)


class ESXTests(TestCase):

    def setUp(self):
        self.raw_esx = Mock()
        self.raw_esx.name = "esx-name"
        self.wrapped_esx = ESX(self.raw_esx)

    def test_should_passthrough_unwrapped_attributes(self):
        self.assertEqual(self.wrapped_esx.anything, self.raw_esx.anything)

    def test_should_equal_to_esx_with_same_name(self):
        other_raw_esx = Mock()
        other_raw_esx.name = "esx-name"
        other_esx = ESX(other_raw_esx)

        self.assertTrue(self.wrapped_esx == other_esx)

    def test_should_not_equal_to_esx_with_other_name(self):
        other_raw_esx = Mock()
        other_raw_esx.name = "other-esx-name"
        other_esx = ESX(other_raw_esx)

        self.assertFalse(self.wrapped_esx == other_esx)

    def test_should_raise_when_number_of_cores_not_in_resources(self):
        resources = []
        self.raw_esx.licensableResource.resource = resources

        self.assertRaises(RuntimeError, self.wrapped_esx.get_number_of_cores)

    def test_should_return_number_of_cores_when_in_resources(self):
        resource_1 = Mock()
        resource_1.key = "weLoveCamelCase"
        resource_2 = Mock()
        resource_2.key = "numCpuCores"
        resource_2.value = 42
        resource_3 = Mock()
        resource_3.key = "someOtherKey"

        resources = [resource_1, resource_2, resource_3]
        self.raw_esx.licensableResource.resource = resources

        self.assertEquals(self.wrapped_esx.get_number_of_cores(), 42)

class getAllVMInFolderTests(TestCase):

    def test_should_resolve_deep_nesting(self):
        vm_1 = lambda: None
        vm_1.name = "vm-1"
        vm_2 = lambda: None
        vm_2.name = "vm-2"
        level_2_nesting = [vm_2]
        child_folder = Mock()
        child_folder.childEntity = level_2_nesting
        level_1_nesting = [vm_1, child_folder]
        root_folder = Mock()
        root_folder.childEntity = level_1_nesting

        actual_vms = [vm for vm in get_all_vms_in_folder(root_folder)]

        self.assertEqual(len(actual_vms), 2)
        self.assertEqual(actual_vms[0].raw_vm, vm_1)
        self.assertEqual(actual_vms[1].raw_vm, vm_2)
