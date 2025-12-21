from curvtools.cli.curvcfg.cli_helpers.delayed_param.resolveable import Resolvable
from curvtools.cli.curvcfg.cli_helpers.delayed_param.resolveable_factory import make_resolvable_param_type
from curvtools.cli.curvcfg.cli_helpers.paramtypes.profile import Profile
from curvtools.cli.curvcfg.cli_helpers.paramtypes.device import Device
from curvtools.cli.curvcfg.cli_helpers.paramtypes.board import Board
from curvtools.cli.curvcfg.cli_helpers.paramtypes.merged_toml import MergedToml
from curvtools.cli.curvcfg.cli_helpers.opts.fs_path_opt import make_fs_path_param_type_class

ProfileResolvable = Resolvable[Profile]
profile_type = make_resolvable_param_type(
    type_name="profile",
    from_path=lambda p: Profile(p),
    is_input_path=True,
    from_name=Profile.from_name,
)

DeviceResolvable = Resolvable[Device]
device_type = make_resolvable_param_type(
    type_name="device",
    from_path=lambda p: Device(p),
    is_input_path=True,
    from_name=Device.from_name,
)

BoardResolvable = Resolvable[Board]
board_type = make_resolvable_param_type(
    type_name="board",
    from_path=lambda p: Board(p),
    is_input_path=True,
    from_name=Board.from_name,
)

#
# generated/intermediates/merged_board.toml
# 
InputMergedBoardTomlResolvable = Resolvable[MergedToml]
input_merged_board_toml_type = make_resolvable_param_type(
    type_name="merged_board_toml",
    from_path=lambda p: MergedToml(p),
    is_input_path=True,
    from_name=MergedToml.from_name,
)
OutputMergedBoardTomlResolvable = Resolvable[MergedToml]
output_merged_board_toml_type = make_resolvable_param_type(
    type_name="merged_toml",
    from_path=lambda p: MergedToml(p),
    is_input_path=False,
    from_name=MergedToml.from_name,
)

#
# generated/intermediates/merged_config.toml
# 
InputMergedConfigTomlResolvable = Resolvable[MergedToml]
input_merged_config_toml_type = make_resolvable_param_type(
    type_name="merged_config_toml",
    from_path=lambda p: MergedToml(p),
    is_input_path=True,
    from_name=MergedToml.from_name,
)
OutputMergedConfigTomlResolvable = Resolvable[MergedToml]
output_merged_config_toml_type = make_resolvable_param_type(
    type_name="merged_config_toml",
    from_path=lambda p: MergedToml(p),
    is_input_path=False,
    from_name=MergedToml.from_name,
)

#
# generated/config/merged.toml
# 
InputMergedTomlResolvable = Resolvable[MergedToml]
input_merged_toml_type = make_resolvable_param_type(
    type_name="merged_toml",
    from_path=lambda p: MergedToml(p),
    is_input_path=True,
    from_name=MergedToml.from_name,
)

OutputMergedTomlResolvable = Resolvable[MergedToml]
output_merged_toml_type = make_resolvable_param_type(
    type_name="merged_toml",
    from_path=lambda p: MergedToml(p),
    is_input_path=False,
    from_name=MergedToml.from_name,
)

#
# schema files
# 
schema_file_type = make_fs_path_param_type_class(
    dir_okay=False,
    file_okay=True,
    exists=True
)