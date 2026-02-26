### Could not find the AD Kernel for this --> DerivativeTwoPhaseMaterial

[Mesh]
    type = GeneratedMesh
    dim = 2
    nx = 50
    ny = 50
    xmin = 0
    xmax = 100
    ymin = 0
    ymax = 100
    elem_type = QUAD9
[]

[ICs]
    [eta1]
        variable = eta1
        type = FunctionIC
        function = 'if(y>=40&y<=60 & x>=40&x<=60, 1, 0)'
    []

    [eta2]
        variable = eta2
        type = FunctionIC
        function = 'if(y>=40&y<=60 & x>=40&x<=60, 0, 1)'
    []
[]

[BCs]
  [Periodic]
    [eta1]
      auto_direction = 'x y'
    []
  []
[]


[Variables]
    [eta1]
        order = FIRST
        family = LAGRANGE
    []

    [eta2]
        order = FIRST
        family = LAGRANGE
    []
[]


[Materials]
    [scale]
        type = ADGenericConstantMaterial
        prop_names = 'length_scale   time_scale   energy_scale   v_mol'
        prop_values = '1.0            1.0          1.0        1.0' 
    []

    [constants]
        type = ADGenericConstantMaterial
        prop_names = 'sigma delta   M1   M2  '
        prop_values = '0.5   1      1     1  '
    []

    [F_1]
        type = ADDerivativeParsedMaterial
        property_name = F1
        material_property_names = 'length_scale energy_scale v_mol'
        coupled_variables = 'eta1'
        constant_names     =   'a1   b1   c1  e1'
        constant_expressions = '10   0   -10  1'
        expression = '(a1*(eta1-e1)^2 +b1*(eta1-e1) +c1)*energy_scale/(v_mol*length_scale^3)'
        # expression = '(10*(eta1-0)^2 + 0*(eta1-0) - 10) *1/(1*1^3) '
    []


    [F_2]
        type = ADDerivativeParsedMaterial
        property_name = F2
        material_property_names = 'length_scale energy_scale v_mol'
        coupled_variables = 'eta2'
        constant_names = 'a2   b2   c2  e2'
        constant_expressions = '5.8  0   -5  0'
        expression = '(a2*(eta2-e2)^2 +b2*(eta2-e2) + c2)*energy_scale/(v_mol*length_scale^3)'
    []


    [h1]
        type = ADDerivativeParsedMaterial
        property_name = h1
        # expression = '3*eta1^2 - 2*eta1^3'
        expression = '3*(if(eta1 > 1, 1, if(eta1 < 0, 0, eta1)))^2 - 2*(if(eta1 > 1, 1, if(eta1 < 0, 0, eta1)))^3'
        coupled_variables = 'eta1'
        derivative_order = 2
        outputs = exodus
    []


    [h2]
        type = ADDerivativeParsedMaterial
        property_name = h2
        expression = '3*(if(eta2 > 1, 1, if(eta2 < 0, 0, eta2)))^2 - 2*(if(eta2 > 1, 1, if(eta2 < 0, 0, eta2)))^3'
        coupled_variables = 'eta2'
        derivative_order = 2
        outputs = exodus
    []

    [g1]
        type = BarrierFunctionMaterial
        g_order = SIMPLE
        eta = eta1
        function_name = g1
    []

    [g2]
        type = BarrierFunctionMaterial
        g_order = SIMPLE
        eta = eta1
        function_name = g2
    []

    [mu]
        type = ADParsedMaterial
        property_name = mu
        material_property_names = 'sigma delta energy_scale length_scale'
        expression = '6*(sigma/delta)*(energy_scale/length_scale^3)'
    []

    [kappa_value]
        type = ADParsedMaterial
        property_name = kappa
        material_property_names = 'sigma delta energy_scale length_scale'
        expression = '0.75*(sigma*delta)*(energy_scale/length_scale)'
    []
  
    [L1-2]
        type = ADParsedMaterial
        property_name = L1_2
        material_property_names = 'M1         mu    M2 kappa'
        expression = '((4/3)*(mu/kappa))*((M1+M2)/(2*0.2))'
    []
    
    [Interface_Mobility]
        type = ADDerivativeParsedMaterial
        property_name = L
        coupled_variables = 'eta1 eta2'
        material_property_names = 'L1_2 h1 h2'
        expression = 'L1_2*h1*h2'
    []

    [free_energy]
        type = ADDerivativeParsedMaterial
        property_name = F
        #material_property_names = 'F1  F2 h1 h2 g1_AD g2_AD'
        material_property_names = 'F1(eta1) F2(eta2) h1(eta1) h2(eta2) g1_AD(eta1) g2_AD(eta2)'
        coupled_variables = 'eta1 eta2'
        constant_names = 'W'
        constant_expressions = '0.0'
        expression = 'h1*F1 + h2*F2 + W*(g1_AD + g2_AD)'
        derivative_order = 2
        outputs = exodus
    []

    [g_converter_to_ad]
        type = MaterialADConverter
        reg_props_in = 'g1 g2'
        ad_props_out = 'g1_AD g2_AD'
    []


[]

[Kernels]
   # Kernels for Allen-Cahn equation for eta1
    [deta1dt]
        type = ADTimeDerivative
        variable = eta1
    []

    [ACInterface1]
        type = ADACInterface
        variable = eta1
        kappa_name = kappa
        mob_name = L
        variable_L = False
    []

    [ACBulk1]
        type = ADAllenCahn
        variable = eta1
        f_name = F
        mob_name = L
    []

   # Kernels for Allen-Cahn equation for eta2
    [deta2dt]
        type = ADTimeDerivative
        variable = eta2
    []

    [ACInterface2]
        type = ADACInterface
        variable = eta2
        kappa_name = kappa
        mob_name = L
        variable_L = False
    []

    [ACBulk2]
        type = ADAllenCahn
        variable = eta2
        f_name = F
        mob_name = L
    []
[]


[Executioner]
    type = Transient
    solve_type          = 'PJFNK'

    # petsc_options_iname = '-pc_type -pc_hypre_type -ksp_gmres_restart -pc_hypre_boomeramg_strong_threshold'
    # petsc_options_value = 'hypre    boomeramg      31       0.7'
    
    petsc_options       = '-snes_converged_reason -ksp_converged_reason -options_left'
    petsc_options_iname = '-ksp_gmres_restart -pc_factor_shift_type -pc_factor_shift_amount -pc_type'
    petsc_options_value = '100 NONZERO 1e-15 ilu'

    l_max_its           = 30
    nl_max_its          = 50
    l_tol               = 1e-04
    nl_rel_tol          = 1e-08
    nl_abs_tol          = 1e-09

    end_time            = 28.0
    dt                  = 0.06

   # [Adaptivity]
   #     initial_adaptivity = 1
   #     refine_fraction = 1.1
   #     coarsen_fraction = 0.1
   #     max_h_level = 1
   #     # weight_names = 'eta1 eta2'
   #     # weight_values = '1 1'
   # []

[]


[Preconditioning]
    
    active = 'SMP_full'

    [SMP_full]
        type = SMP
        full = true
        petsc_options_iname = '-pc_type -pc_factor_shift_type -pc_factor_mat_solver_type'
        petsc_options_value = 'lu       NONZERO               strumpack'
    []

    [mydebug]
        type = FDP
        full = true
    []
[]

[Postprocessors]
    # Area of Phases
   [area_h1]
       type = ADElementIntegralMaterialProperty
       mat_prop = h1
       execute_on = 'Initial TIMESTEP_END'
   []

   [area_h2]
       type = ADElementIntegralMaterialProperty
       mat_prop = h2
       execute_on = 'Initial TIMESTEP_END'
   []
[]

[Outputs]
    exodus = true
    time_step_interval = 1
    file_base = exodus/2Phase
    csv = true
  [my_checkpoint]
    type = Checkpoint
    num_files = 2
    time_step_interval = 2
    file_base = exodus/2Phase
  []
[]

[Debug]
    show_var_residual_norms = true
[]
