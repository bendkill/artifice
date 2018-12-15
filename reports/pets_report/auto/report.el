(TeX-add-style-hook
 "report"
 (lambda ()
   (TeX-add-to-alist 'LaTeX-provided-class-options
                     '(("IEEEtran" "10pt" "journal")))
   (TeX-add-to-alist 'LaTeX-provided-package-options
                     '(("subfig" "caption=false" "font=footnotesize")))
   (add-to-list 'LaTeX-verbatim-macros-with-braces-local "hyperref")
   (add-to-list 'LaTeX-verbatim-macros-with-braces-local "hyperimage")
   (add-to-list 'LaTeX-verbatim-macros-with-braces-local "hyperbaseurl")
   (add-to-list 'LaTeX-verbatim-macros-with-braces-local "nolinkurl")
   (add-to-list 'LaTeX-verbatim-macros-with-braces-local "url")
   (add-to-list 'LaTeX-verbatim-macros-with-braces-local "path")
   (add-to-list 'LaTeX-verbatim-macros-with-delims-local "path")
   (TeX-run-style-hooks
    "latex2e"
    "IEEEtran"
    "IEEEtran10"
    "amsmath"
    "amsfonts"
    "amssymb"
    "hyperref"
    "graphicx"
    "subfig")
   (LaTeX-add-labels
    "sec:introduction"
    "tab:dataset-summary"
    "sec:conclusion")
   (LaTeX-add-bibliographies
    "IEEEabrv"
    " report"))
 :latex)
