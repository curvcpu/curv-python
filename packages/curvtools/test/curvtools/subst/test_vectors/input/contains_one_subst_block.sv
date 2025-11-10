`ifndef TB_DISPLAY_SVH
`define TB_DISPLAY_SVH

package tb_display;

    function void print_if_id_pipereg(input if_id_pipereg_t if_id_pipereg);
        // @subst[`python -c "print(' '.join([str(i) for i in range(0,10)]))"`]
        // @endsubst
    endfunction

endpackage

`endif