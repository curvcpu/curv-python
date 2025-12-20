//
// boardpkg package (machine generated)
//
package boardpkg;

    // used by top module's port definitions
    localparam int LEDS_COUNT = 8; // lpf_name = leds
    localparam int BTN_COUNT  = 6; // lpf_name = btn

    typedef enum logic [$clog2(BTN_COUNT+1)-1:0] {
        B1 = 0,
        B2 = 1,
        UP = 2,
        DOWN = 3,
        LEFT = 4,
        RIGHT = 5,
        BTN_NONE = BTN_COUNT // this constant should always be set to 1 greater than the highest button index
    } btn_id_t;

   typedef struct packed {
         logic [BTN_COUNT-1:0] pressed;  // high for 1 cycle upon short press+release of any button or combo
         logic is_shift_down;            // flag that indicates the press event occurred with the shift button held
         logic is_long_press;            // flag that indicates the press event was a long press
   } btn_event_t;

endpackage
