#ifndef blah
    #define blah(x) x// something fun
    #include __FILE__
    #undef blah
#endif

#ifndef blah
    #define blah(x) x x// something else that is also fun
    #include __FILE__
    #undef blah
#endif

#ifdef blah
    blah(foo)
    blah(bar)
#endif
