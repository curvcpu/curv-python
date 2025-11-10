`ifndef TB_DISPLAY_SVH
`define TB_DISPLAY_SVH

`ifdef SLANG
    // slang header:  machine generated; customize in settings.json: mwg-verilog-helpers.slangIncludes=[]
    `include "defines/riscv_defines.svh"
    `include "cache/cachepkg.svh"
    `include "ulx3s.vh"
    `include "buttons/ulx3s_buttons_defines.sv"
    `include "oled/typedefs.sv"
    `ifdef MINI_CACHE
        `include "tb/ram_hex_cache4/ram_hex_files_paths.vh"
    `else
        `include "tb/ram_hex/ram_hex_files_paths.vh"
    `endif
    `ifndef SIMULATION
        `define SIMULATION
    `endif
    `include "verilator/lib/tb_util.svh"
    `include "verilator/lib/tb_assertions.svh"
`endif

`ifdef VERILATOR
    // veril header:  machine generated; customize in settings.json: mwg-verilog-helpers.verilatorIncludes=[]
    `include "rvpkg.sv"
    `ifdef MINI_CACHE
        `include "ram_hex_cache4/ram_hex_files_paths.vh"
    `else
        `include "ram_hex/ram_hex_files_paths.vh"
    `endif
    `include "tb_util.svh"
    `include "tb_assertions.svh" 
`endif


package tb_display;

    import rvpkg::*;
    import cachepkg::*;
    import tb_assertions::*;
    import tb_util::*;

    //////////////////////////////////////////////////////////////
    //
    // Helper functions
    //
    //////////////////////////////////////////////////////////////

    // verilator lint_off WIDTHTRUNC 
    
    ////////////////////////////////////////////////////////////////////////////////
    // Debug print functions
    ////////////////////////////////////////////////////////////////////////////////
    function logic [31:0] build_physical_addr(input [cachepkg::ICACHE_OFFSET_BITS-1:0] offset, input [cachepkg::ICACHE_IDX_BITS-1:0] idx, input [cachepkg::ICACHE_TAG_BITS-1:0] tag);
        return {22'b0, tag , idx , offset , 2'b0};
    endfunction

    /*
    function void print_wb_ram();
        $display("wb_ram:");
        for (int i = 0; i < BRAM_SIZE_WORDS; i++) begin
            $display("  ram[%d]=%h", i, wishbone_ram_uut.ram[i]);
        end
    endfunction

    function void print_wishbone_bram(logic [31:0] timestamp);
            $display("+-------------------------------------------------+");
            $display("|               Wishbone BRAM Dump                |");
            $display("+-------------------------------------------------+");
            $display("|      st=%6d, Time: %t, State: %s", timestamp, $realtime, uut.state_str);
            $display("+-------------------------------------------------+");
            $display("|      Address       |           Value            |");
            $display("+--------------------+----------------------------+");
        

            for (int i = 0; i < BRAM_SIZE_WORDS; i++) begin
                $display("|     0x%8h     |          %8h          |", i, wishbone_ram_uut.ram[i]);
            end

            $display("+--------------------+----------------------------+");
    endfunction
    */

    function void print_test_header(input string test_name, input string test_description);
        $display(" +============================================================================================================================================================================");
        $display(" |  Starting Test: %s", test_name);
        $display(" |  %s", test_description);
        $display(" +=============================================================================================================================================================================");
    endfunction

    // verilator lint_off VARHIDDEN
    /*
    function string mk_state_substate_str(input logic[5:0] state, input string state_str, input string flush_all_substate_str, input string writeback_substate_str);
        if (state==cachepkg::IDLE) begin
            return "IDLE";
        end else if (state==cachepkg::FLUSH_ALL) begin
            return $sformatf("FLUSH_ALL [%s]", flush_all_substate_str);
        end else if (state==cachepkg::WRITE_BACK) begin
            return $sformatf("WRITE_BACK [%s]", writeback_substate_str);
        end else begin
            return $sformatf("%s", state_str);
        end
    endfunction
    */
    // verilator lint_on VARHIDDEN


    ////////////////////////////////////////////////////////////////////////////////
    //
    // Check that signal changes during the next clock cycle
    //
    ////////////////////////////////////////////////////////////////////////////////
    /*
    typedef enum { MISS, HIT_WAY_0, HIT_WAY_1, IF_STALL } signal_id_t;
    string signal_names [4] = {"MISS", "HIT_WAY_0", "HIT_WAY_1", "IF_STALL"};
    function automatic string get_signal_name(input signal_id_t which);
        return signal_names[which];
    endfunction
    function automatic logic get_signal_value(input signal_id_t which);
        case (which)
            MISS: return uut.miss;
            HIT_WAY_0: return uut.hits[0];
            HIT_WAY_1: return uut.hits[1];
            IF_STALL: return uut.if_stall_o;
            default: return 1'bx;
        endcase
    endfunction
    typedef struct {
        signal_id_t which;
        logic expected;
        string expected_str;
        int line;
        string test_name;
        logic display_success;
    } scheduled_check_t;
    scheduled_check_t signals_to_check[int][$];
    function automatic void schedule_check_midway_through_next_clock_cycle(input signal_id_t which, input logic expected, input string expected_str, int line, string test_name, input logic display_success = 1'b0);
        scheduled_check_t signal_to_check;
        signal_to_check.which = which;
        signal_to_check.expected = expected;
        signal_to_check.expected_str = expected_str;
        signal_to_check.line = line;
        signal_to_check.test_name = test_name;
        signal_to_check.display_success = display_success;
        $display("[%t] ⏳ scheduling signal check >>> for %s to become %s (currently: %b) before next rising edge", $realtime, get_signal_name(which), expected_str, get_signal_value(which));
        signals_to_check[int'($realtime+15)].push_back(signal_to_check);
    endfunction
    always @(negedge clk) begin
        if (signals_to_check.exists(int'($realtime))) begin
            scheduled_check_t check;
            scheduled_check_t queue_at_time[$];
            queue_at_time = signals_to_check[int'($realtime)];
            foreach (queue_at_time[i]) begin
                check = queue_at_time[i];
                if (get_signal_value(check.which) == check.expected) begin
                    if (check.display_success) begin
                        $display("[%t] ✅ 🕰️ scheduled check: actual=1'b%b == expected=%s (%s at line %s)", $realtime, get_signal_value(check.which), check.expected_str, check.test_name, trim($sformatf("%d", check.line)));
                    end
                end else begin
                    $display("[%t] ❌ 🕰️ scheduled check: ASSERTION FAILED: actual=1'b%b != expected=%s (%s at line %s)", $realtime, get_signal_value(check.which), check.expected_str, check.test_name, trim($sformatf("%d", check.line)));
                    $fatal;
                end
            end
            signals_to_check.delete(int'($realtime));
        end
    end
    */

    ////////////////////////////////////////////////////////////////////////////////
    //
    // Pipeline register print functions
    //
    ////////////////////////////////////////////////////////////////////////////////
    function void print_if_id_pipereg(input if_id_pipereg_t if_id_pipereg);
    endfunction

    function void print_pc(input logic [31:0] pc, input logic [31:0] pc_next, input logic [31:0] instr_if);
        $display("[%t] +--------------------------------------+", $realtime);
        $display("[%t] | pipeline                             |", $realtime);
        $display("[%t] +---------+----------------------------+", $realtime);
        $display("[%t] | pc      | %04h                       |", $realtime, pc);
        $display("[%t] | pc_next | %04h                       |", $realtime, pc_next);
        $display("[%t] | instr   | %04h                       |", $realtime, instr_if);
        $display("[%t] +---------+----------------------------+", $realtime);
    endfunction
    // verilator lint_off WIDTHTRUNC

endpackage

`endif