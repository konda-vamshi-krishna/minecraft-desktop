
import os, re, math, unittest

class TestPhysicsSpecification(unittest.TestCase):
    AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
    H_FILE = os.path.join(AGENT_DIR, 'proposed_physics.h')
    C_FILE = os.path.join(AGENT_DIR, 'proposed_physics.c')

    def setUp(self):
        with open(self.H_FILE, 'r', encoding='utf-8') as f:
            self.h_content = f.read()
        with open(self.C_FILE, 'r', encoding='utf-8') as f:
            self.c_content = f.read()

    def test_01_zero_dynamic_heap_allocations(self):
        forbidden = [r'malloc', r'calloc', r'realloc', r'free']
        for f_name, content in [('proposed_physics.h', self.h_content), ('proposed_physics.c', self.c_content)]:
            for pattern in forbidden:
                match = re.search(pattern, content)
                self.assertIsNone(match, f'Forbidden dynamic allocation {pattern} found in {f_name}')

    def test_02_ponytail_comments_present(self):
        self.assertIn('ponytail:', self.h_content)
        self.assertIn('ponytail:', self.c_content)

    def test_03_canonical_constants_in_header(self):
        expected_constants = [
            ('PLAYER_WIDTH', '0.60f'),
            ('PLAYER_HALF_WIDTH', '0.30f'),
            ('PLAYER_HEIGHT_STANDING', '1.80f'),
            ('PLAYER_HEIGHT_SNEAKING', '1.50f'),
            ('PLAYER_EYE_OFFSET_STANDING', '1.62f'),
            ('PLAYER_EYE_OFFSET_SNEAKING', '1.35f'),
            ('PLAYER_SPEED_WALK', '4.317f'),
            ('PLAYER_SPEED_SPRINT', '5.612f'),
            ('PLAYER_SPEED_SNEAK', '1.295f'),
            ('PHYSICS_GRAVITY', '-32.0f'),
            ('PHYSICS_TERMINAL_VELOCITY', '-78.4f'),
            ('PHYSICS_GROUND_FRICTION', '0.546f'),
            ('PHYSICS_AIR_DRAG', '0.980f'),
            ('PHYSICS_AUTOSTEP_HEIGHT', '0.550f'),
            ('PHYSICS_SUBSTEP_THRESHOLD', '0.500f')
        ]
        for name, val in expected_constants:
            self.assertIn(f'#define {name}', self.h_content)
            self.assertIn(val, self.h_content)

    def test_04_mathematical_discrete_recurrence_terminal_velocity(self):
        vy = 0.0
        for _ in range(1000):
            vy = (vy - 0.08) * 0.98
        terminal_blocks_per_tick = vy
        terminal_si_m_per_s = terminal_blocks_per_tick * 20.0
        self.assertAlmostEqual(terminal_blocks_per_tick, -3.92, places=4)
        self.assertAlmostEqual(terminal_si_m_per_s, -78.4, places=4)

    def test_05_mathematical_jump_impulse_apex_clearance(self):
        y = 0.0
        vy = 0.42
        max_y = 0.0
        for tick in range(15):
            y += vy
            if y > max_y:
                max_y = y
            vy = (vy - 0.08) * 0.98
        self.assertAlmostEqual(max_y, 1.2522, places=3)
        self.assertGreater(max_y, 1.250)

    def test_06_continuous_jump_impulse_kinematics(self):
        v = 8.9442719
        g = 32.0
        h = (v ** 2) / (2.0 * g)
        self.assertAlmostEqual(h, 1.250, places=3)

    def test_07_interface_contract_functions(self):
        required_fn_prototypes = [
            'Physics_InitPlayer',
            'Physics_UpdateHitbox',
            'Physics_GetAABBAt',
            'Physics_GetEyePosition',
            'Physics_GetInterpolatedRenderPosition',
            'Physics_GetInterpolatedEyePosition',
            'Physics_Step',
            'Physics_StepEx',
            'Physics_CheckCollision',
            'Physics_CheckCollisionEx',
            'Physics_HasGroundSupport',
            'Physics_Raycast',
            'Physics_RaycastEx',
            'Physics_ValidateBlockPlacement'
        ]
        for fn in required_fn_prototypes:
            self.assertIn(fn, self.h_content, 'Missing prototype ' + fn + ' in proposed_physics.h')
            self.assertIn(fn, self.c_content, 'Missing implementation ' + fn + ' in proposed_physics.c')

if __name__ == '__main__':
    unittest.main()
